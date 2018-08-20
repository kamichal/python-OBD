
import pytest
import time

from obd import commands, Unit


# NOTE: This is purposefully tuned slightly higher than the ELM's default
#       message timeout of 200 milliseconds. This prevents us from
#       inadvertently marking the first query of an async connection as
#       null, since it may be the case that the first transaction incurs the
#       ELM's internal timeout.
STANDARD_WAIT_TIME = 0.3


def skip_if_no_port_specified(function):
    reason = "needs --port=<port> to run"
    missing_port_option = not pytest.config.getoption("--port")
    decorator = pytest.mark.skipif(missing_port_option, reason=reason)
    return decorator(function)


@pytest.fixture(scope="module")
def obd(request):
    """provides an OBD connection object for obdsim"""
    import obd
    port = request.config.getoption("--port")
    return obd.OBD(port)


@pytest.fixture(scope="module")
def async_obd(request):
    """provides an OBD *Async* connection object for obdsim"""
    import obd
    port = request.config.getoption("--port")
    return obd.Async(port)


def good_rpm_response(r):
    return (not r.is_null()) and \
           (r.value.u == Unit.rpm) and \
           (r.value >= 0.0 * Unit.rpm)


@skip_if_no_port_specified
def test_supports(obd):
    assert(len(obd.supported_commands) > 0)
    assert(obd.supports(commands.RPM))


@skip_if_no_port_specified
def test_rpm(obd):
    r = obd.query(commands.RPM)
    assert(good_rpm_response(r))


# Async tests

@skip_if_no_port_specified
def test_async_query(async_obd):

    rs = []
    async_obd.watch(commands.RPM)
    async_obd.start()

    for i in range(5):
        time.sleep(STANDARD_WAIT_TIME)
        rs.append(async_obd.query(commands.RPM))

    async_obd.stop()
    async_obd.unwatch_all()

    # make sure we got data
    assert(len(rs) > 0)
    assert(all([good_rpm_response(r) for r in rs]))


@skip_if_no_port_specified
def test_async_callback(async_obd):

    rs = []
    async_obd.watch(commands.RPM, callback=rs.append)
    async_obd.start()
    time.sleep(STANDARD_WAIT_TIME)
    async_obd.stop()
    async_obd.unwatch_all()

    # make sure we got data
    assert(len(rs) > 0)
    assert(all([good_rpm_response(r) for r in rs]))


@skip_if_no_port_specified
def test_async_paused(async_obd):

    assert(not async_obd.running)
    async_obd.watch(commands.RPM)
    async_obd.start()
    assert(async_obd.running)

    with async_obd.paused() as was_running:
        assert(not async_obd.running)
        assert(was_running)

    assert(async_obd.running)
    async_obd.stop()
    assert(not async_obd.running)


@skip_if_no_port_specified
def test_async_unwatch(async_obd):

    watched_rs = []
    unwatched_rs = []

    async_obd.watch(commands.RPM)
    async_obd.start()

    for i in range(5):
        time.sleep(STANDARD_WAIT_TIME)
        watched_rs.append(async_obd.query(commands.RPM))

    with async_obd.paused():
        async_obd.unwatch(commands.RPM)

    for i in range(5):
        time.sleep(STANDARD_WAIT_TIME)
        unwatched_rs.append(async_obd.query(commands.RPM))

    async_obd.stop()

    # the watched commands
    assert(len(watched_rs) > 0)
    assert(all([good_rpm_response(r) for r in watched_rs]))

    # the unwatched commands
    assert(len(unwatched_rs) > 0)
    assert(all([r.is_null() for r in unwatched_rs]))


@skip_if_no_port_specified
def test_async_unwatch_callback(async_obd):

    a_rs = []
    b_rs = []
    async_obd.watch(commands.RPM, callback=a_rs.append)
    async_obd.watch(commands.RPM, callback=b_rs.append)

    async_obd.start()
    time.sleep(STANDARD_WAIT_TIME)

    with async_obd.paused():
        async_obd.unwatch(commands.RPM, callback=b_rs.append)

    time.sleep(STANDARD_WAIT_TIME)
    async_obd.stop()
    async_obd.unwatch_all()

    assert(all([good_rpm_response(r) for r in a_rs + b_rs]))
    assert(len(a_rs) > len(b_rs))
