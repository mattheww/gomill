"""Test support code for testing gomill GTP engines.

(Which includes proxy engines.)

"""

def check_engine(tc, engine, command, args, expected,
                 expect_failure=False, expect_end=False,
                 expect_internal_error=False):
    """Send a command to an engine and check its response.

    tc                    -- TestCase
    engine                -- Gtp_engine_protocol
    command               -- GTP command to send
    args                  -- list of GTP arguments to send
    expected              -- expected response string (None to skip check)
    expect_failure        -- expect a GTP failure response
    expect_end            -- expect the engine to report 'end session'
    expect_internal_error -- see below

    If the response isn't as expected, uses 'tc' to report this.

    If expect_internal_error is true, expect_failure is forced true, and the
    check for expected (if specified) is that it's included in the response,
    rather than equal to the response.

    """
    failure, response, end = engine.run_command(command, args)
    if expect_internal_error:
        expect_failure = True
    if expect_failure:
        tc.assertTrue(failure,
                      "unexpected GTP success response: %s" % response)
    else:
        tc.assertFalse(failure,
                       "unexpected GTP failure response: %s" % response)
    if expect_internal_error:
        tc.assertTrue(response.startswith("internal error\n"), response)
        if expected is not None:
            tc.assertTrue(expected in response, response)
    elif expected is not None:
        if command == "showboard":
            tc.assertDiagramEqual(response, expected,
                                  "showboard response not as expected")
        else:
            tc.assertEqual(response, expected, "GTP response not as expected")
    if expect_end:
        tc.assertTrue(end, "expected end-session not seen")
    else:
        tc.assertFalse(end, "unexpected end-session")

