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


import re


from libversion import ANY_IS_PATCH, P_IS_PATCH, version_compare


class VersionClass:
    newest = 1
    outdated = 2
    ignored = 3
    unique = 4
    devel = 5
    legacy = 6
    incorrect = 7
    untrusted = 8
    noscheme = 9
    rolling = 10

    @staticmethod
    def IsIgnored(cl):
        """Return whether a specified class is equivalent to ignored."""
        return (cl == VersionClass.ignored or
                cl == VersionClass.incorrect or
                cl == VersionClass.untrusted or
                cl == VersionClass.noscheme or
                cl == VersionClass.rolling)

    @staticmethod
    def ToString(cl):
        """Return string representation of a version class."""
        return {
            VersionClass.newest: 'newest',
            VersionClass.outdated: 'outdated',
            VersionClass.ignored: 'ignored',
            VersionClass.unique: 'unique',
            VersionClass.devel: 'devel',
            VersionClass.legacy: 'legacy',
            VersionClass.incorrect: 'incorrect',
            VersionClass.untrusted: 'untrusted',
            VersionClass.noscheme: 'noscheme',
            VersionClass.rolling: 'rolling',
        }[cl]


class PackageFlags:
    # remove package
    remove = 1 << 0

    # devel version
    devel = 1 << 1

    # ignored variants
    ignore = 1 << 2
    incorrect = 1 << 3
    untrusted = 1 << 4
    noscheme = 1 << 5

    any_ignored = ignore | incorrect | untrusted | noscheme

    rolling = 1 << 7  # is processed differently than other ignoreds

    # forced classes
    outdated = 1 << 8
    legacy = 1 << 9

    # special flags
    p_is_patch = 1 << 10
    any_is_patch = 1 << 11

    @staticmethod
    def GetMetaorder(cl):
        """Return a higher order version sorting key based on flags.

        E.g. rolling versions always precede normal versions,
        and normal versions always precede outdated versions

        Within a specific metaorder versions are compared normally
        """
        if cl & PackageFlags.rolling:
            return 1
        if cl & PackageFlags.outdated:
            return -1
        return 0


class PackageSanityCheckProblem(Exception):
    pass


class PackageSanityCheckFailure(PackageSanityCheckProblem):
    pass


class Package:
    __slots__ = [
        'repo',
        'family',
        'subrepo',

        'name',
        'effname',

        'version',
        'origversion',
        'versionclass',

        'maintainers',
        'category',
        'comment',
        'homepage',
        'licenses',
        'downloads',

        'flags',
        'shadow',
        'verfixed',

        'flavors',

        'extrafields',
    ]

    def __init__(self, repo=None, family=None, subrepo=None,
                 name=None, effname=None,
                 version=None, origversion=None, versionclass=None,
                 maintainers=None, category=None, comment=None, homepage=None, licenses=None, downloads=None,
                 flags=0, shadow=False, verfixed=False,
                 flavors=None,
                 extrafields=None):
        self.repo = repo
        self.family = family
        self.subrepo = subrepo

        self.name = name
        self.effname = effname

        self.version = version
        self.origversion = origversion
        self.versionclass = versionclass

        self.maintainers = maintainers if maintainers else []
        self.category = category
        self.comment = comment
        self.homepage = homepage
        self.licenses = licenses if licenses else []
        self.downloads = downloads if downloads else []

        self.flags = flags
        self.shadow = shadow
        self.verfixed = verfixed

        self.flavors = flavors if flavors else []

        self.extrafields = extrafields if extrafields else {}

    def CheckSanity(self, transformed=True):
        # checks
        def NoNewlines(value):
            return 'contains newlines' if '\n' in value else ''

        def NoSlashes(value):
            return 'contains slashes' if '/' in value else ''

        def Stripped(value):
            return 'is not stripped' if value != value.strip() else ''

        def Alphanumeric(value):
            return 'contains not allowed symbols' if not re.fullmatch('[a-zA-Z0-9_-]+', value) else ''

        def Lowercase(value):
            return 'is not lowercase' if value != value.lower() else ''

        def NoWhitespace(value):
            return 'contains whitespace' if re.search('[ \t\n\r]', value) else ''

        def NonEmpty(value):
            return 'is empty' if value == '' else ''

        # checkers
        def CheckBool(value, name):
            if not isinstance(value, bool):
                raise PackageSanityCheckFailure('{}: {} is not a boolean'.format(self.name, name))

        def CheckStr(value, name, *checks):
            if not isinstance(value, str):
                raise PackageSanityCheckFailure('{}: {} is not a string'.format(self.name, name))
            for check in checks:
                result = check(value)
                if result:
                    raise PackageSanityCheckProblem('{}: {} {}: "{}"'.format(self.name, name, result, value))

        def CheckList(value, name, *checks):
            if not isinstance(value, list):
                raise PackageSanityCheckFailure('{}: {} is not a list'.format(self.name, name))
            for element in value:
                CheckStr(element, name, *checks)

        def CheckDict(value, name, *checks):
            if not isinstance(value, dict):
                raise PackageSanityCheckFailure('{}: {} is not a dict'.format(self.name, name))
            for element in value.values():
                CheckStr(element, name, *checks)

        def CheckInt(value, name):
            if not isinstance(value, int):
                raise PackageSanityCheckFailure('{}: {} is not an int'.format(self.name, name))

        CheckStr(self.repo, 'repo', NoNewlines, Stripped, Alphanumeric, Lowercase)
        CheckStr(self.family, 'family', NoNewlines, Stripped, Alphanumeric, Lowercase)
        if self.subrepo is not None:
            CheckStr(self.subrepo, 'subrepo', NoNewlines, Stripped)

        CheckStr(self.name, 'name', NoNewlines, Stripped, NonEmpty)
        if transformed or self.effname is not None:
            CheckStr(self.effname, 'effname', NoNewlines, Stripped, NonEmpty, NoSlashes)

        CheckStr(self.version, 'version', NoNewlines, Stripped, NonEmpty)
        if self.origversion is not None:
            CheckStr(self.origversion, 'origversion', NoNewlines, Stripped)

        CheckList(self.maintainers, 'maintainers', NoNewlines, Stripped, NoWhitespace, NoSlashes, NonEmpty)
        if self.category is not None:
            CheckStr(self.category, 'category', NoNewlines, Stripped, NonEmpty)
        if self.comment is not None:
            CheckStr(self.comment, 'comment', NoNewlines, Stripped, NonEmpty)
        if self.homepage is not None:
            CheckStr(self.homepage, 'homepage', NoWhitespace, NonEmpty)
        CheckList(self.licenses, 'licenses', NoNewlines, Stripped, NonEmpty)
        CheckList(self.downloads, 'downloads', NoWhitespace, NoNewlines, NonEmpty)

        CheckInt(self.flags, 'flags')
        CheckBool(self.shadow, 'shadow')
        CheckBool(self.verfixed, 'verfixed')

        CheckList(self.flavors, 'flavors', NoNewlines, Stripped, NonEmpty)

        CheckDict(self.extrafields, 'extrafields', NoWhitespace, NonEmpty)

    def Normalize(self):
        # normalize homepage (currently adds / to url which points to host)
        if self.homepage:
            match = re.fullmatch('(https?://)([^/]+)(/.*)?', self.homepage, re.IGNORECASE)

            if match:
                schema = match.group(1).lower()
                hostname = match.group(2).lower()
                path = match.group(3) or '/'

                self.homepage = schema + hostname + path

        # unicalize and sort maintainers list
        if len(self.maintainers) > 1:
            self.maintainers = sorted(set(self.maintainers))

    def CheckFormat(self):
        # check
        for slot in self.__slots__:
            if not hasattr(self, slot):
                return False

        return True

    # setters
    def SetFlag(self, flag, isset=True):
        if isset:
            self.flags |= flag
        else:
            self.flags &= ~flag

    # getters
    def HasFlag(self, flag):
        return self.flags & flag

    # other helper methods
    def VersionCompare(self, other):
        self_metaorder = PackageFlags.GetMetaorder(self.flags)
        other_metaorder = PackageFlags.GetMetaorder(other.flags)

        if self_metaorder < other_metaorder:
            return -1
        if self_metaorder > other_metaorder:
            return 1

        return version_compare(
            self.version,
            other.version,
            ((self.flags & PackageFlags.p_is_patch) and P_IS_PATCH) |
            ((self.flags & PackageFlags.any_is_patch) and ANY_IS_PATCH),
            ((other.flags & PackageFlags.p_is_patch) and P_IS_PATCH) |
            ((other.flags & PackageFlags.any_is_patch) and ANY_IS_PATCH)
        )

    @property
    def __dict__(self):
        return {slot: getattr(self, slot) for slot in self.__slots__}

    def __eq__(self, other):
        return self.__dict__ == other.__dict__
