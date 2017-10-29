import subprocess

dfu = "dfu-util"

dfu_help = '''
The device is probably not in DFU mode
    1. Make sure the USB cable is connected to your desktop (host).
    2. Press the BOOT button on Core Module and keep it pressed.
            BOOT button is on the right side and is marked with letter "B".
    3. Press the RESET button on Core Module while BOOT button is still held.
            RESET button is on the left side and is marked with letter "R".
    4. Release the RESET button.
    5. Release the BOOT button.
'''

dfu_help_install = '''
Please install dfu-util:
sudo apt install dfu-util
Or from https://sourceforge.net/projects/dfu-util/files/?source=navbar
'''


def test():
    try:
        subprocess.check_output([dfu, "--version"])
        return True
    except Exception:
        return False


def run(filename_bin):
    if not test():
        print(dfu_help_install)
        return False

    cmd = [dfu, "-s", "0x08000000:leave", "-d", "0483:df11", "-a", "0", "-D", filename_bin]

    status = subprocess.call(cmd)
    if status:
        print("=" * 60)
        print(dfu_help)
        return False


def get_list_devices():
    table = []
    try:
        proc = subprocess.Popen([dfu, '--list'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    except Exception:
        return table

    while 1:
        line = proc.stdout.readline()
        if not line and proc.poll() is not None:
            break
        line = line.decode()
        if line.startswith("Found DFU:"):
            serial = line.split()[-1]
            serial = 'dfu:' + serial[serial.find('"') + 1:-1]
            if serial not in table:
                table.append(serial)
    return table
