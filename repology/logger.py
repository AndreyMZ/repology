# Copyright (C) 2016-2017 Dmitry Marakasov <amdmi3@amdmi3.ru>
#
# This file is part of repology
#
# repology is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# repology is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with repology.  If not, see <http://www.gnu.org/licenses/>.

import sys
import time


try:
    from fcntl import flock, LOCK_EX
except ImportError:
    LOCK_EX = 0
    def flock(fd, op):
        pass


class Logger:
    def Log(self, message):
        raise NotImplementedError()

    def GetPrefixed(self, prefix):
        raise NotImplementedError()

    def GetIndented(self, level=1):
        return self.GetPrefixed('  ' * level)


class NoopLogger(Logger):
    def __init__(self):
        pass

    def Log(self, message):
        pass

    def GetPrefixed(self, prefix):
        return NoopLogger()


class FileLogger(Logger):
    def __init__(self, path, prefix=None):
        self.path = path
        self.prefix = prefix

    def Log(self, message):
        prefixstr = self.prefix if self.prefix else ''
        with open(self.path, 'a', encoding='utf-8') as logfile:
            flock(logfile, LOCK_EX)
            print(time.strftime('%b %d %T ') + prefixstr + message,
                  file=logfile)

    def GetPrefixed(self, prefix):
        return FileLogger(self.path,
                          self.prefix + prefix if self.prefix else prefix)


class StderrLogger(Logger):
    def __init__(self, prefix=None):
        self.prefix = prefix

    def Log(self, message):
        prefixstr = self.prefix if self.prefix else ''
        print(time.strftime('%b %d %T ') + prefixstr + message,
              file=sys.stderr)

    def GetPrefixed(self, prefix):
        return StderrLogger(self.prefix + prefix if self.prefix else prefix)
