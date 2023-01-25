# Copyright 2004-2023 Tom Rothamel <pytom@bishoujo.us>
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation files
# (the "Software"), to deal in the Software without restriction,
# including without limitation the rights to use, copy, modify, merge,
# publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# This is the config module, where game configuration settings are stored.
# This includes both simple settings (like the screen dimensions) and
# methods that perform standard tasks, like the say and menu methods.

init -1100 python:

    # True if Ren'Py's Save Sync is enabled, False otherwise.
    config.has_sync = True

    # The server to sync against, to allow sync against a test server.
    config.sync_server = "https://sync.renpy.org"

    class UploadSync(Action):

        def __call__(self):
            renpy.invoke_in_new_context(_sync.upload)

        def get_sensitive(self):
            return config.has_sync

    class DownloadSync(Action):

        def __call__(self):
            if renpy.invoke_in_new_context(_sync.download):
                renpy.notify(_("Sync downloaded."))

        def get_sensitive(self):
            return config.has_sync

init 1100 python:

    if config.savedir is not None:
        config.extra_savedirs.append(config.savedir + "/sync")
    else:
        config.has_sync = None

    if renpy.emscripten and PY2:
        config.has_sync = None

init -1100 python in _sync:

    # Do not participate in saves.
    _constant = True

    from renpy.store import renpy, config

    # The digits used by a sync.
    DIGITS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"

    # If not None, a sync id that we'll use for testing.
    TEST_SYNC_ID = None

    def check_sync_id(sync_id):
        """
        Checks to see if a sync id is valid.
        """

        if len(sync_id) != 11:
            return False

        if sync_id[5] != "-":
            return False

        for i in sync_id[:5] + sync_id[6:]:
            if i not in DIGITS:
                return False

        return True

    def get_sync_id():
        """
        Returns a unique random id that can be used to identify a sync.
        """

        if TEST_SYNC_ID is not None:
            return TEST_SYNC_ID

        import random

        n = random.SystemRandom().getrandbits(64)

        rv = ""

        for i in range(5):
            rv += DIGITS[n % 36]
            n //= 36

        rv += "-"

        for i in range(5):
            rv += DIGITS[n % 36]
            n //= 36

        return rv

    def key_and_hash(sync_id):
        """
        Return a 32 byte key and 32-character hash, from a sync_id.
        """

        import hashlib

        hashed = sync_id.encode("utf-8")

        for _ in range(10000):
            hashed = hashlib.sha256(hashed).digest()

        key = hashed

        for _ in range(10000):
            hashed = hashlib.sha256(hashed).digest()

        if PY2:
            return key, hashed[16:].encode("hex")
        else:
            return key, hashed[16:].hex()

    def requests_error(e):
        import requests

        renpy.display.log.write("Sync error:")
        renpy.display.log.exception()

        if isinstance(e, requests.exceptions.ConnectionError):
            return _("Could not connect to the Ren'Py Sync server.")
        elif isinstance(e, requests.exceptions.Timeout):
            return _("The Ren'Py Sync server timed out.")
        else:
            return _("An unknown error occurred while connecting to the Ren'Py Sync server.")

    if renpy.emscripten:

        def upload_content(content, hashed):
            """
            Uploads content to the sync server, using the given half-hash.

            Returns None on success, or an error message on failure.
            """

            import emscripten
            import time
            import os

            with open("/sync.data", "wb") as f:
                f.write(content)

            fetch_id = emscripten.run_script_int(
                """fetchFile("PUT", "{url}", "/sync.data", null)""".format(
                    url=config.sync_server + "/api/sync/v1/" + hashed
            ))

            status = "PENDING"
            message = "Pending."

            start = time.time()
            while start - time.time() < 15:
                renpy.pause(0)

                result = emscripten.run_script_string("""fetchFileResult({})""".format(fetch_id))
                status, _ignored, message = result.partition(" ")

                if status != "PENDING":
                    break

            os.unlink("/sync.data")

            if status != "OK":
                return message
            else:
                return None


        def download_content(hashed):
            import emscripten
            import time
            import os

            fetch_id = emscripten.run_script_int(
                """fetchFile("GET", "{url}", null, "/sync.data")""".format(
                    url=config.sync_server + "/api/sync/v1/" + hashed
            ))

            status = "PENDING"
            message = "Pending."

            start = time.time()
            while start - time.time() < 15:
                renpy.pause(0)

                result = emscripten.run_script_string("""fetchFileResult({})""".format(fetch_id))
                status, _ignored, message = result.partition(" ")

                if status != "PENDING":
                    break

            if status == "OK":
                with open("/sync.data", "rb") as f:
                    data = f.read()

                os.unlink("/sync.data")

                return False, data

            else:
                if "404" in message:
                    return True, _("The Ren'Py Sync server does not have a copy of this sync. The sync ID may be invalid, or it may have timed out.")
                else:
                    return True, message

    else:

        def upload_content(content, hashed):
            """
            Uploads content to the sync server, using the given half-hash.

            Returns None on success, or an error message on failure.
            """

            import requests

            try:
                r = requests.put(config.sync_server + "/api/sync/v1/" + hashed, data = content, timeout=15)
            except Exception as e:
                return requests_error(e)

            if r.status_code != 200:
                return r.text

            return None

        def download_content(hashed):
            """
            Downloads content from the sync server, using the given half-hash.

            Returns True and an error message on errro, and False and the content on success.
            """

            import requests

            try:
                r = requests.get(config.sync_server + "/api/sync/v1/" + hashed, timeout=15)
            except Exception as e:
                return True, requests_error(e)

            if r.status_code == 404:
                return True, _("The Ren'Py Sync server does not have a copy of this sync. The sync ID may be invalid, or it may have timed out.")
            elif r.status_code != 200:
                return True, r.text

            return False, r.content

    def report_error(message):
        renpy.call_screen("sync_error", message)

    def upload():

        if not config.has_sync:
            return

        if not renpy.call_screen("sync_confirm"):
            return

        renpy.save_persistent()

        SIZE_LIMIT = 10 * 1024 * 1024

        import io
        import zipfile
        import os

        bio = io.BytesIO()

        # A list of mtime, filename paits
        files = [ ]

        location = renpy.loadsave.location

        for i in location.list():
            if i.startswith("_"):
                continue

            if i.startswith("auto-"):
                continue

            if i.startswith("quick-") and i != "quick-1":
                continue

            files.append((location.mtime(i), i + "-LT1.save"))

        files.sort(reverse=True)

        with zipfile.ZipFile(bio, "w", zipfile.ZIP_STORED) as zf:

            total_size = 0

            persistent = location.path("persistent")[1]

            if persistent is not None:
                total_size += os.path.getsize(persistent)

                if total_size < SIZE_LIMIT:
                    zf.write(persistent, "persistent")

            for _mtime, fn in files:
                path = location.path(fn)[1]

                if path is None:
                    continue

                total_size += os.path.getsize(path)

                if total_size > SIZE_LIMIT:
                    break

                zf.write(path, fn)

        contents = bio.getvalue()
        del bio

        sync_id = get_sync_id()
        key, hashed = key_and_hash(sync_id)

        contents = renpy.encryption.secretbox_encrypt(contents, key)

        error = upload_content(contents, hashed)

        if error:
            report_error(error)
            return

        # Show the sync id to the player.

        renpy.call_screen("sync_success", sync_id)

    def download():

        if not config.has_sync:
            return

        # Get and check the sync id.

        sync_id = renpy.input(
            _("Please enter the sync ID you generated.\nNever enter a sync ID you didn't create yourself."),
            default=TEST_SYNC_ID if TEST_SYNC_ID else "",
            allow=DIGITS + "-",
            length=11,
            screen="sync_prompt",
            )

        sync_id = sync_id.strip().upper()

        if not sync_id:
            return

        if not check_sync_id(sync_id):
            report_error(_("The sync id is not in the correct format."))
            return

        key, hashed = key_and_hash(sync_id)

        # Download the sync from the server.

        error, content = download_content(hashed)

        if error:
            report_error(content)
            return

        # Decrypt the sync.

        try:
            content = renpy.encryption.secretbox_decrypt(content, key)
        except ValueError:
            report_error(_("The sync could not be decrypted."))
            return

        # Unzip the sync.

        import io
        import zipfile

        with zipfile.ZipFile(io.BytesIO(content), "r") as zf:
            for fn in zf.namelist():
                if "/" in fn or "\\" in fn:
                    report_error(_("The sync contains a file with an invalid name."))
                    return

            zf.extractall(config.savedir + "/sync")

        renpy.loadsave.location.scan()

        if renpy.emscripten:
            import emscripten
            emscripten.syncfs()

        return True

init -100:

    screen sync_confirm():
        modal True
        zorder 100

        use confirm(
            _("This will upload your saves to the {a=https://sync.renpy.org}Ren'Py Sync Server{/a}.\nDo you want to continue?"),
            yes_action=Return(True),
            no_action=Return(False))

    screen sync_prompt(prompt):
        modal True
        zorder 100

        add "gui/overlay/confirm.png"

        frame:
            xalign .5
            yalign .5
            xpadding gui.scale(40)
            ypadding gui.scale(40)

            vbox:
                spacing gui.scale(30)

                label _("Enter Sync ID"):
                    xalign 0.5

                text prompt:
                    xalign 0.5
                    text_align 0.5

                input:
                    id "input"
                    xalign 0.5

                text _("This will contact the {a=https://sync.renpy.org}Ren'Py Sync Server{/a}."):
                    xalign 0.5
                    text_align 0.5

                textbutton _("Cancel"):
                    action Return("")
                    xalign 0.5

        ## Right-click and escape answer "no".
        key "game_menu" action Return(False)


    screen sync_success(sync_id):
        modal True
        zorder 100

        add "gui/overlay/confirm.png"

        frame:
            xalign .5
            yalign .5
            xpadding gui.scale(40)
            ypadding gui.scale(40)

            vbox:
                spacing gui.scale(30)

                label _("Sync Success"):
                    xalign 0.5

                text _("The Sync ID is:"):
                    xalign 0.5

                text sync_id:
                    xalign 0.5

                text _("You can use this ID to download your save on another device.\nThis sync will expire in an hour.\nRen'Py Sync is supported by {a=https://www.renpy.org/sponsors.html}Ren'Py's Sponsors{/a}."):
                    xalign 0.5
                    text_align 0.5

                textbutton _("Continue"):
                    action Return(True)
                    xalign 0.5

        ## Right-click and escape answer "no".
        key "game_menu" action Return(False)

    screen sync_error(message):
        modal True
        zorder 100

        add "gui/overlay/confirm.png"

        frame:
            xalign .5
            yalign .5
            xpadding gui.scale(40)
            ypadding gui.scale(40)

            vbox:
                spacing gui.scale(30)

                label _("Sync Error"):
                    xalign 0.5

                text message:
                    xalign 0.5

                textbutton _("Continue"):
                    action Return(True)
                    xalign 0.5

        ## Right-click and escape answer "no".
        key "game_menu" action Return(False)