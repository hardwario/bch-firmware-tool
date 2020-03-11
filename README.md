<a href="https://www.hardwario.com/"><img src="https://www.hardwario.com/ci/assets/hw-logo.svg" width="200" alt="HARDWARIO Logo" align="right"></a>

# Host Application - HARDWARIO Firmware Tool

[![Travis](https://img.shields.io/travis/bigclownlabs/bch-firmware-tool/master.svg)](https://travis-ci.org/bigclownlabs/bch-firmware-tool)
[![Release](https://img.shields.io/github/release/bigclownlabs/bch-firmware-tool.svg)](https://github.com/bigclownlabs/bch-firmware-tool/releases)
[![License](https://img.shields.io/github/license/bigclownlabs/bch-firmware-tool.svg)](https://github.com/bigclownlabs/bch-firmware-tool/blob/master/LICENSE)
[![PyPI](https://img.shields.io/pypi/v/bcf.svg)](https://pypi.org/project/bcf/)
[![Twitter](https://img.shields.io/twitter/follow/hardwario_en.svg?style=social&label=Follow)](https://twitter.com/hardwario_en)

This repository contains HARDWARIO Firmware Tool.

## Installing

You can install **bcf** directly from PyPI:

```sh
sudo pip3 install -U bcf
```

For Bash Complete add this line to `.bashrc`
```
eval "$(_BCF_COMPLETE=source bcf)"
```
Then run this command to reload .bashrc
```
source ~/.bashrc
```
Now you can for example write `bcf --de`, press TAB and `--device` text is automatically completed.

## Usage

```
>>> bcf help

Usage: bcf [OPTIONS] COMMAND [ARGS]...

  HARDWARIO Firmware Tool.

Options:
  -d, --device TEXT  Device path.
  --version          Show the version and exit.
  --help             Show this message and exit.

Commands:
  clean    Clean cache.
  create   Create new firmware.
  devices  Print available devices.
  eeprom   Work with EEPROM.
  flash    Flash firmware.
  help     Show help.
  list     List firmware.
  log      Show log.
  pull     Pull firmware to cache.
  read     Download firmware to file.
  reset    Reset core module.
  search   Search in firmware names and descriptions.
  update   Update list of available firmware.
```


## License

This project is licensed under the [MIT License](https://opensource.org/licenses/MIT/) - see the [LICENSE](LICENSE) file for details.

---

Made with &#x2764;&nbsp; by [**HARDWARIO s.r.o.**](https://www.hardwario.com/) in the heart of Europe.
