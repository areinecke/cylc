#!/bin/bash
#C: THIS FILE IS PART OF THE CYLC SUITE ENGINE.
#C: Copyright (C) 2008-2014 Hilary Oliver, NIWA
#C:
#C: This program is free software: you can redistribute it and/or modify
#C: it under the terms of the GNU General Public License as published by
#C: the Free Software Foundation, either version 3 of the License, or
#C: (at your option) any later version.
#C:
#C: This program is distributed in the hope that it will be useful,
#C: but WITHOUT ANY WARRANTY; without even the implied warranty of
#C: MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#C: GNU General Public License for more details.
#C:
#C: You should have received a copy of the GNU General Public License
#C: along with this program.  If not, see <http://www.gnu.org/licenses/>.
#-------------------------------------------------------------------------------
# Test cylc get-job-status, "at" jobs
. $(dirname $0)/test_header
#-------------------------------------------------------------------------------
set_test_number 12

function get_fake_job_id() {
    # Choose a non existent PID
    local T_JOB_ID=$RANDOM
    while [[ $(atq 2>/dev/null | cut -f1) == $T_JOB_ID ]]; do
        T_JOB_ID=$RANDOM
    done
    echo $T_JOB_ID
}

function get_real_job_id() {
    echo 'sleep 10' | at now 2>&1 \
        | sed '/^job [^ ]\+ at/!d; s/^job \([^ ]\+\) at.*$/\1/'
}
#-------------------------------------------------------------------------------
TEST_NAME=$TEST_NAME_BASE-null
# A non-existent status file
T_ST_FILE=$PWD/$TEST_NAME.1.status
T_JOB_ID=$(get_fake_job_id)
run_ok $TEST_NAME cylc get-job-status $T_ST_FILE at $T_JOB_ID
cmp_ok $TEST_NAME.stdout <<__OUT__
polled $TEST_NAME submission failed
__OUT__
#-------------------------------------------------------------------------------
TEST_NAME=$TEST_NAME_BASE-submitted
# A non-existent status file
T_ST_FILE=$PWD/$TEST_NAME.1.status
# Give it a real PID
T_JOB_ID=$(get_real_job_id)
run_ok $TEST_NAME cylc get-job-status $T_ST_FILE at $T_JOB_ID
cmp_ok $TEST_NAME.stdout <<__OUT__
polled $TEST_NAME submitted
__OUT__
atrm $T_JOB_ID 2>/dev/null
#-------------------------------------------------------------------------------
TEST_NAME=$TEST_NAME_BASE-started
# Give it a real PID
T_JOB_ID=$(get_real_job_id)
# Status file
T_ST_FILE=$PWD/$TEST_NAME.1.status
T_INIT_TIME=$(date +%FT%H:%M:%S)
cat >$T_ST_FILE <<__STATUS__
CYLC_JOB_PID=$T_JOB_ID
CYLC_JOB_INIT_TIME=$T_INIT_TIME
__STATUS__
run_ok $TEST_NAME cylc get-job-status $T_ST_FILE at $T_JOB_ID
cmp_ok $TEST_NAME.stdout <<__OUT__
polled $TEST_NAME started at $T_INIT_TIME
__OUT__
atrm $T_JOB_ID 2>/dev/null
#-------------------------------------------------------------------------------
TEST_NAME=$TEST_NAME_BASE-succeeded
T_JOB_ID=$(get_fake_job_id)
# Status file
T_ST_FILE=$PWD/$TEST_NAME.1.status
T_INIT_TIME=$(date +%FT%H:%M:%S)
T_EXIT_TIME=$(date +%FT%H:%M:%S)
cat >$T_ST_FILE <<__STATUS__
CYLC_JOB_PID=$T_JOB_ID
CYLC_JOB_INIT_TIME=$T_INIT_TIME
CYLC_JOB_EXIT=SUCCEEDED
CYLC_JOB_EXIT_TIME=$T_EXIT_TIME
__STATUS__
run_ok $TEST_NAME cylc get-job-status $T_ST_FILE at $T_JOB_ID
cmp_ok $TEST_NAME.stdout <<__OUT__
polled $TEST_NAME succeeded at $T_EXIT_TIME
__OUT__
#-------------------------------------------------------------------------------
TEST_NAME=$TEST_NAME_BASE-failed
T_JOB_ID=$(get_fake_job_id)
# Status file
T_ST_FILE=$PWD/$TEST_NAME.1.status
T_INIT_TIME=$(date +%FT%H:%M:%S)
T_EXIT_TIME=$(date +%FT%H:%M:%S)
cat >$T_ST_FILE <<__STATUS__
CYLC_JOB_PID=$T_JOB_ID
CYLC_JOB_INIT_TIME=$T_INIT_TIME
CYLC_JOB_EXIT=ERR
CYLC_JOB_EXIT_TIME=$T_EXIT_TIME
__STATUS__
run_ok $TEST_NAME cylc get-job-status $T_ST_FILE at $T_JOB_ID
cmp_ok $TEST_NAME.stdout <<__OUT__
polled $TEST_NAME failed at $T_EXIT_TIME
__OUT__
#-------------------------------------------------------------------------------
TEST_NAME=$TEST_NAME_BASE-failed-bad
T_JOB_ID=$(get_fake_job_id)
# Status file
T_ST_FILE=$PWD/$TEST_NAME.1.status
T_INIT_TIME=$(date +%FT%H:%M:%S)
T_EXIT_TIME=$(date +%FT%H:%M:%S)
cat >$T_ST_FILE <<__STATUS__
CYLC_JOB_PID=$T_JOB_ID
CYLC_JOB_INIT_TIME=$T_INIT_TIME
__STATUS__
run_ok $TEST_NAME cylc get-job-status $T_ST_FILE at $T_JOB_ID
cmp_ok $TEST_NAME.stdout <<__OUT__
polled $TEST_NAME failed at unknown-time
__OUT__
#-------------------------------------------------------------------------------
exit
