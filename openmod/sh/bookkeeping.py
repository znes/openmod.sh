""" A special module for classes and functions that do boring bookkeping.

Sometimes tedious bookkeping is better factored out into objects or functions
tailored especially for doing this sort of thing. This module gives this code a
home so that it doesn't obscure the actual relevant parts in the code that
needs to do bookkeping on top of it's regular duties.
"""

from uuid import uuid4
import os
import signal

from flask.sessions import (SessionInterface as SI, SessionMixin as SM)


class Job():
    """ A convenience class enhancing `multiprocessing.pool.AsyncResult` with additional information.
    """
    def __init__(self, result, connection, name, user):
        """
        Parameters
        ----------

        result: multiprocessing.pool.AsyncResult
            The `AsyncResult` object for which additional information should
            be tracked.
        connection: multiprocessing.Connection
            The connection which allows us to communicate with the child
            process.
        name: str
            The name of the scenario for which the job computes results.
        user: str
            The name of the user who started the job.
        """
        self._status = False
        self.connection = connection
        self.result = result
        self.name = name
        self.user = user

    def key(self):
        return str(id(self.result))

    def get(self):
        return self.result.get()

    def ready(self):
        return self.result.ready()

    def status(self):
        if self._status:
            return self._status
        if self.ready():
            s = self.get()
            if s[0:len("Stopped.")] == "Stopped.":
                return "Stopped."
            elif s[0:len("Success.")] == "Success.":
                return "Done."
            elif s[0:len("Failure.")] == "Failure.":
                return "Failed."
            elif s[0:len("Cancelled.")] == "Cancelled.":
                return "Cancelled."
        elif self.connection.poll():
            return "Running."
        else:
            return "Queued."
        return "Something's wrong. Please file a bug."

    def cancel(self):
        c = self.connection
        try:
            c.send("Cancel!");
            if c.poll():
                pid = c.recv()
                os.kill(pid, signal.SIGINT)
                self._status = "Stopped."
            else:
                self._status = "Cancelled."
        except BrokenPipeError as e:
            # That's ok. It just means the worker has already stopped.
            pass

    def dead(self):
        return (not self.status() in ["Queued.", "Running."])


class InMemorySession(dict, SM):
    def __init__(self, sid, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.sid = sid

class InMemorySessionInterface(dict, SI):

    def _generate_sid(self):
        return str(uuid4())

    def open_session(self, app, request):
        sid = request.cookies.get(app.session_cookie_name)
        if not sid:
          sid = self._generate_sid()
          return InMemorySession(sid)

        return InMemorySession(sid, self.get(sid, {}))

    def save_session(self, app, session, response):
        if not session:
            if session.modified:
                if session.sid in self:
                    del self[session.sid]
                response.delete_cookie(app.session_cookie_name,
                                       domain=self.get_cookie_domain(app),
                                       path=self.get_cookie_path(app))
        self[session.sid] = self.get(session.sid, {})
        self[session.sid].update(dict(session))
        response.set_cookie(app.session_cookie_name, session.sid,
                            expires=self.get_expiration_time(app, session),
                            httponly=self.get_cookie_httponly(app),
                            domain=self.get_cookie_domain(app),
                            path=self.get_cookie_path(app),
                            secure=self.get_cookie_secure(app))


class PointIds:
    """ Keeps track of the virtual ids used to communicate with the iD editor.

    Sometimes POINT geometries are created only in order to communicate with
    the iD editor. These points are only used in one session and have to use
    ids which are consistent within this session, but are otherwise not
    persisted. As these ids have to be generated on the fly, they might clash
    with ids already used in the database. Therefore this class is used to keep
    track of which ids are already in use so that new virtual ones can be
    generated in case of a clash.
    This is done by just calling objects of this class as a function. See the
    documentation of the __call__ method for details.
    IMPORTANT: This is basically a memory leak on the server. It means that
               objects are kept alive for the lifetime of a session. That means
               that long lived sessions may fill up memory. If this becomes a
               performance or even security problem, we may have to start
               persisting generated points to the database to keep the
               session's memory footprint constant.
    """

    def __init__(self):
        self.oid = {}
        self.vid = {}
        self.min = 0

    def __call__(self, oid=None, vid=None):
        """ Check whether oid matches vid or return the missing parameter.

        If both oid, i.e. object id, and vid, i.e. virtual id are supplied,
        the return a boolean value signallign whether both ids correspond to
        each other or not.
        If only one of these parameters are supplied, return the corresponding
        missing one.
        For convenience sake, not supplying anything returns `None`.
        """
        if oid is not None:
            if vid is not None:
                return self.oid[vid] == self.vid[oid]
            else:
                return self.vid.get(oid, self.new_vid(oid))
        else:
            if vid is not None:
                return self.oid[vid]
            else:
                return None

    def new_vid(self, oid):
        """ Given an unknown oid, generates and returns a new vid for it.
        """
        if not oid in self.vid:
            self.oid[oid] = oid
            self.vid[oid] = oid
            return oid
        while self.min in self.oid:
            self.min = self.min + 1
        self.oid[self.min] = oid
        self.vid[oid] = self.min
        return self.min

