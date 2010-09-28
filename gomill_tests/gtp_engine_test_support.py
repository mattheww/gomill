"""Test support code for testing gomill GTP engines.

(Which includes proxy engines.)

"""

def check_engine(tc, engine, command, args, expected,
                 expect_failure=False, expect_end=False):
    """Send a command to an engine and check its response.

    tc             -- TestCase
    engine         -- Gtp_engine_protocol
    command        -- GTP command to send
    args           -- list of GTP arguments to send
    expected       -- expected response string
    expect_failure -- expect a GTP failure response
    expect_end     -- expect the engine to report 'end session'

    If the response isn't as expected, uses 'tc' to report this.

    """
    failure, response, end = engine.run_command(command, args)
    if expect_failure:
        tc.assertTrue(failure,
                      "unexpected GTP success response: %s" % response)
    else:
        tc.assertFalse(failure,
                       "unexpected GTP failure response: %s" % response)
    tc.assertEqual(response, expected, "GTP response not as expected")
    if expect_end:
        tc.assertTrue(end, "expected end-session not seen")
    else:
        tc.assertFalse(end, "unexpected end-session")


