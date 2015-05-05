# encoding: utf-8

"""
Package for configuration of version numbers.
"""


class IncomparableVersions(TypeError):
    """
    Two versions could not be compared.
    """


class Version(object):

    def __init__(self, package, major, minor, patch, prerelease=None):
        """


        Args:
            package (str): Package name
            major (int): Major version number
            minor (int): Minor version number
            patch (int): Patch number

        Kwargs:
            prerelease (str): pre-release specifier
        """
        self.package = package
        self.major = major
        self.minor = minor
        self.patch = patch
        self.prerelease = prerelease

    def short(self):
        """
        Return a string in short version format,
        <major>.<minor>
        """
        return "{major}.{minor}".format(**self.__dict__)

    def long(self):
        """
        Return a string in version format,
        <major>.<minor>.<patch>[-prerelease]
        """
        s = "{major}.{minor}.{patch}".format(**self.__dict__)
        if self.prerelease:
            s = "{}-{}".format(s, self.prerelease)
        return s

    def __repr__(self):
        return "[{}, version {}]".format(self.package, self.long())

    def __str__(self):
        return "[{}, version {}]".format(self.package, self.long())

    def __cmp__(self, other):
        """
        Compare two versions, considering major versions, minor versions, micro
        versions, then prereleases.

        A version with a prerelease is always less than a version without a
        prerelease. All prerelease string are considered identical in value.

        Args:

            other (Version): Another version.

        Returns:

            one of -1, 0, or 1.

        Raises:
            - NotImplementedError: when the other version is not a Version
              object
            - IncomparableVersions: when the package names of the versions
              differ.
        """
        if not isinstance(other, self.__class__):
            raise NotImplementedError
        if self.package != other.package:
            raise IncomparableVersions(
                "{} != {}".format(self.package, other.package))

        if self.prerelease:
            pre = 0
        else:
            pre = 1
        if other.prerelease:
            otherpre = 0
        else:
            otherpre = 1

        x = cmp(
            (self.major,
             self.minor,
             self.patch,
             pre),
            (other.major,
             other.minor,
             other.patch,
             otherpre))
        return x

# vim:set ft=python sw=4 et spell spelllang=en:
