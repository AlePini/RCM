# std lib
import sys
import os
import types
import inspect

root_rcm_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(root_rcm_path)

# local includes
from server import rcm_protocol_server
from client.miscellaneous.logger import logic_logger


def rcm_decorate(fn):
    name = fn.__name__
    code = fn.__code__
    argcount = code.co_argcount
    argnames = code.co_varnames[:argcount]

    from functools import wraps

    @wraps(fn)
    def wrapper(*args, **kw):
        """
        This is the wrapper for functions into ssh command line, it add debug info before calling actual command
        It uses mycall defined in manager to get return from ssh command output
        """
        command = '--command=' + name
        for p in list(kw.keys()):
            if p in argnames:
                command += ' --' + p + '=' + kw[p]
        logic_logger.debug("calling " + name + " argnames-> " + str(argnames))
        logic_logger.debug(str(kw) + " -- " + str(args))
        logic_logger.debug("self-->" + str(args[0]))
        logic_logger.debug("running remote:" + command)
        ret = args[0].mycall(command)
        return ret
    return wrapper


for name, fn in inspect.getmembers(rcm_protocol_server.rcm_protocol):
    if sys.version_info >= (3, 0):
        # look for user-defined member functions
        if isinstance(fn, types.FunctionType) and name[:2] != '__':
            logic_logger.debug("wrapping-->" + name)
            setattr(rcm_protocol_server.rcm_protocol, name, rcm_decorate(fn))
    else:
        if isinstance(fn, types.MethodType) and name[:2] != '__':
            logic_logger.debug("wrapping-->"+name)
            setattr(rcm_protocol_server.rcm_protocol, name, rcm_decorate(fn))


def get_protocol():
    return rcm_protocol_server.rcm_protocol()


if __name__ == '__main__':
    def prex(command='', commandnode=''):
        return "prex:node " + commandnode + " run -->" + command + "<--"

    r = get_protocol()
    for i in ['uno', 'due', 'tre']:
        def mycall(command):
            return prex(command, i)
        logic_logger.debug("config return:", r.config(build_platform='mia_build_platform_' + i))
        logic_logger.debug("queue return:", r.queue())
