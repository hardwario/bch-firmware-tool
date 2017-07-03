import subprocess

dfu_help = '''
The device is probably not in DFU mode
    1. Make sure the USB cable is connected to your desktop (host).
    2. Press the BOOT button on Core Module and keep it pressed.
            BOOT button is on the right side and is marked with letter "B".
    3. Press the RESET button on Core Module while BOOT button is still held.
            BOOT button is on the left side and is marked with letter "R".
    4. Release the RESET button.
    5. Release the BOOT button.
'''


def run(filename_bin):
    dfu = "dfu-util"
    try:
        subprocess.check_output([dfu, "--version"])
    except Exception:
        print("Please install dfu-util:")
        print("sudo apt install dfu-util")
        print("Or from https://sourceforge.net/projects/dfu-util/files/?source=navbar")
        return False

    cmd = [dfu, "-s", "0x08000000:leave", "-d", "0483:df11", "-a", "0", "-D", filename_bin]

    status = subprocess.call(cmd)
    if status:
        print("=" * 60)
        print(dfu_help)
        return False
