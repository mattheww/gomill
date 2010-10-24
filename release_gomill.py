"""Package a gomill release."""

import os
import re
import shutil
import sys
from optparse import OptionParser
from subprocess import check_call, CalledProcessError, Popen, PIPE

def check_output(*args, **kwargs):
    """Version of Python 2.7's subprocess.check_output."""
    process = Popen(stdout=PIPE, *args, **kwargs)
    output, unused_err = process.communicate()
    retcode = process.poll()
    if retcode:
        raise CalledProcessError(retcode, args[0], output=output)
    return output

class Failure(StandardError):
    pass

def read_python_file(pathname):
    dummy = {}
    result = {}
    f = open(pathname)
    exec f in dummy, result
    f.close()
    return result

def is_safe_tag(s):
    if s in (".", ".."):
        return False
    return bool(re.search(r"\A[-_.a-zA-Z0-9]+\Z", s))

def is_acceptable_version(s):
    if s in (".", ".."):
        return False
    if len(s) > 12:
        return False
    return bool(re.search(r"\A[-_.a-zA-Z0-9]+\Z", s))

def export_tag(dst, repo_dir, tag):
    """Export from the git tag.

    repo_dir -- git repository to export from (must contain .git)
    tag      -- tag to export
    dst      -- directory to export into

    The exported tree will be placed in a directory named <tag> inside <dst>.

    All files have the timestamp of the commit referred to by the tag.

    """
    if not os.path.isdir(os.path.join(repo_dir, ".git")):
        raise Failure("No .git repo in %s" % repo_dir)
    try:
        check_call("git archive --remote=%s --prefix=%s/ %s | tar -C %s -xf -" %
                   (repo_dir, tag, tag, dst),
                   shell=True)
    except CalledProcessError:
        raise Failure("export failed")

def get_version():
    """Obtain the gomill version from setup.py."""
    try:
        output = check_output("python setup.py --version".split())
    except CalledProcessError:
        raise Failure("'setup.py sdist' failed")
    version = output.strip()
    if not is_acceptable_version(version):
        raise Failure("bad version: %s" % repr(version))
    return version

def make_sdist(version, logfile):
    """Run 'setup.py sdist'.

    cwd must be the distribution directory (gomill_setup).

    Returns the pathname of the sdist tar.gz, relative to the distribution
    directory.

    """
    try:
        check_call("python setup.py sdist".split(), stdout=logfile)
    except CalledProcessError:
        raise Failure("'setup.py sdist' failed")
    result = os.path.join("dist", "gomill-%s.tar.gz" % version)
    if not os.path.exists(result):
        raise Failure("'setup.py sdist' did not create %s" % result)
    return result

def make_sphinx(version, logfile, html_files_to_remove):
    """Run 'setup.py build_sphinx' and make a tarball.

    cwd must be the distribution directory (gomill_setup).

    Returns the pathname of the docs tar.gz, relative to the distribution
    directory.

    """
    try:
        check_call("python setup.py build_sphinx".split(), stdout=logfile)
    except CalledProcessError:
        raise Failure("'setup.py build_sphinx' failed")
    htmlpath = os.path.join("build", "sphinx", "html")
    for filename in html_files_to_remove:
        os.remove(os.path.join(htmlpath, filename))
    os.rename(htmlpath, "gomill-docs-%s" % version)
    try:
        check_call(("tar -czf gomill-docs-%s.tar.gz gomill-docs-%s" %
                    (version, version)).split())
    except CalledProcessError:
        raise Failure("tarring up gomill-docs failed")
    return "gomill-docs-%s.tar.gz" % version

def do_release(tag, config_pathname):
    config_dir = os.path.abspath(os.path.dirname(config_pathname))
    os.chdir(config_dir)

    try:
        config = read_python_file(config_pathname)
    except StandardError, e:
        raise Failure("error reading config file:\n%s" % e)

    export_dir = os.path.join(config['working_dir'], tag)
    dist_dir = os.path.join(export_dir, "gomill_setup")
    if os.path.exists(export_dir):
        shutil.rmtree(export_dir)
    export_tag(config['working_dir'], config['repo_dir'], tag)
    logfile = open(config['log_pathname'], "w")
    os.chdir(dist_dir)
    version = get_version()
    sdist_pathname = make_sdist(version, logfile)
    docs_pathname = make_sphinx(version, logfile,
                                config['html_files_to_remove'])
    os.chdir(config_dir)
    logfile.close()
    sdist_dst = os.path.join(config['target_dir'],
                             os.path.basename(sdist_pathname))
    docs_dst = os.path.join(config['target_dir'],
                            os.path.basename(docs_pathname))
    if os.path.exists(sdist_dst):
        os.remove(sdist_dst)
    if os.path.exists(docs_dst):
        os.remove(docs_dst)
    shutil.move(os.path.join(dist_dir, sdist_pathname), sdist_dst)
    shutil.move(os.path.join(dist_dir, docs_pathname), docs_dst)
    shutil.rmtree(export_dir)


USAGE = """\
%(prog)s <tag>\
"""

def main(argv):
    parser = OptionParser(usage=USAGE)
    opts, args = parser.parse_args(argv)
    if len(args) != 1:
        parser.error("wrong number of arguments")
    tag = args[0]
    if not is_safe_tag(tag):
        parser.error("ill-formed tag")
    config_pathname = os.path.join(
        os.path.abspath(os.path.dirname(__file__)), "release_gomill.conf")
    try:
        if not os.path.exists(config_pathname):
            raise Failure("config file %s does not exist" % config_pathname)
        do_release(tag, config_pathname)
    except (EnvironmentError, Failure), e:
        print >>sys.stderr, "release_gomill.py: %s" % e
        sys.exit(1)

if __name__ == "__main__":
    main(sys.argv[1:])
