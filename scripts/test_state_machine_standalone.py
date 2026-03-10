"""Standalone state machine test -- runs WITHOUT ROS2 or Docker.

Tests the brain_node state transition logic locally on any machine
with just Python installed. No hardware, no ROS2, no Docker needed.

Usage:
    python scripts/test_state_machine_standalone.py
"""

import time
import sys


class State:
    IDLE = 'IDLE'
    SEARCHING = 'SEARCHING'
    APPROACHING = 'APPROACHING'
    WARNING = 'WARNING'
    EXTINGUISHING = 'EXTINGUISHING'
    COMPLETE = 'COMPLETE'


class FakeDetection:
    def __init__(self, detected=False, confidence=0.0, x_center=0.5,
                 y_center=0.5, label=''):
        self.detected = detected
        self.confidence = confidence
        self.x_center = x_center
        self.y_center = y_center
        self.label = label


class StateMachineTester:
    """Mirrors brain_node logic without any ROS2 dependency."""

    def __init__(self):
        self.conf_threshold = 0.6
        self.center_tol = 0.05
        self.approach_dist = 50.0
        self.rot_speed = 0.5
        self.drive_speed = 80.0
        self.search_timeout = 30.0
        self.warning_secs = 5
        self.discharge_duration = 8.0

        self.state = State.IDLE
        self.state_enter_time = time.time()
        self.detection = FakeDetection()
        self.ultrasonic_cm = 999.0
        self.alarm = False
        self.warning_remaining = 0

        self.cmd_vel = (0.0, 0.0)
        self.ext_cmd = 0
        self.warn_cmd = 0

    def set_state(self, new_state):
        if new_state != self.state:
            print(f'  STATE: {self.state} -> {new_state}')
            self.state = new_state
            self.state_enter_time = time.time()

    def time_in_state(self):
        return time.time() - self.state_enter_time

    def publish_twist(self, linear_x=0.0, angular_z=0.0):
        self.cmd_vel = (linear_x, angular_z)

    def tick(self):
        if self.state == State.IDLE:
            if self.alarm:
                self.alarm = False
                self.set_state(State.SEARCHING)
            elif self.detection.detected and self.detection.confidence >= self.conf_threshold:
                self.set_state(State.SEARCHING)

        elif self.state == State.SEARCHING:
            if self.time_in_state() > self.search_timeout:
                self.publish_twist()
                self.set_state(State.IDLE)
                return
            det = self.detection
            if det.detected and det.confidence >= self.conf_threshold:
                error = det.x_center - 0.5
                if abs(error) < self.center_tol:
                    self.publish_twist()
                    self.set_state(State.APPROACHING)
                    return
                direction = -1.0 if error > 0 else 1.0
                self.publish_twist(angular_z=direction * self.rot_speed)
            else:
                self.publish_twist(angular_z=self.rot_speed)

        elif self.state == State.APPROACHING:
            if self.ultrasonic_cm <= self.approach_dist:
                self.publish_twist()
                self.warning_remaining = self.warning_secs
                self.set_state(State.WARNING)
                return
            self.publish_twist(linear_x=self.drive_speed)

        elif self.state == State.WARNING:
            self.publish_twist()
            self.warn_cmd = 1
            elapsed = self.time_in_state()
            remaining = max(0, self.warning_secs - int(elapsed))
            if remaining != self.warning_remaining:
                self.warning_remaining = remaining
                print(f'  WARNING COUNTDOWN: {remaining}s remaining')
            if elapsed >= self.warning_secs:
                self.set_state(State.EXTINGUISHING)

        elif self.state == State.EXTINGUISHING:
            self.warn_cmd = 2
            elapsed = self.time_in_state()
            if elapsed < 2.0:
                self.ext_cmd = 1
            elif elapsed < self.discharge_duration:
                self.ext_cmd = 2
            else:
                self.ext_cmd = 0
                self.set_state(State.COMPLETE)

        elif self.state == State.COMPLETE:
            self.publish_twist()
            self.ext_cmd = 0
            self.warn_cmd = 0
            if self.time_in_state() > 3.0:
                self.set_state(State.IDLE)


def run_test(name, steps):
    print(f'\n{"=" * 50}')
    print(f'  TEST: {name}')
    print(f'{"=" * 50}')
    sm = StateMachineTester()
    for desc, setup_fn, duration, check_fn in steps:
        print(f'\n  >> {desc}')
        if setup_fn:
            setup_fn(sm)
        start = time.time()
        while time.time() - start < duration:
            sm.tick()
            time.sleep(0.05)
        if check_fn:
            result = check_fn(sm)
            status = 'PASS' if result else 'FAIL'
            print(f'  [{status}] State={sm.state} vel={sm.cmd_vel} ext={sm.ext_cmd} warn={sm.warn_cmd}')
        else:
            print(f'  [INFO] State={sm.state} vel={sm.cmd_vel} ext={sm.ext_cmd} warn={sm.warn_cmd}')
    return sm


def main():
    print('FireBot State Machine Standalone Test')
    print('No ROS2 or Docker required.\n')

    all_pass = True

    # Test 1: IDLE -> SEARCHING on fire detection
    def t1_setup(sm):
        sm.detection = FakeDetection(True, 0.85, 0.8, 0.5, 'fire')

    sm = run_test('Fire detection triggers SEARCHING', [
        ('Start in IDLE, inject fire detection (off-center)',
         t1_setup, 0.5,
         lambda sm: sm.state == State.SEARCHING),
    ])
    if sm.state != State.SEARCHING:
        all_pass = False

    # Test 2: SEARCHING -> APPROACHING when fire centered
    def t2_setup(sm):
        sm.detection = FakeDetection(True, 0.85, 0.50, 0.5, 'fire')

    sm = run_test('Centered fire triggers APPROACHING', [
        ('Start in IDLE, inject off-center fire',
         lambda sm: setattr(sm, 'detection', FakeDetection(True, 0.85, 0.8, 0.5, 'fire')),
         0.5, lambda sm: sm.state == State.SEARCHING),
        ('Center the fire (x_center=0.50)',
         t2_setup, 0.5,
         lambda sm: sm.state == State.APPROACHING),
    ])
    if sm.state != State.APPROACHING:
        all_pass = False

    # Test 3: Full scenario IDLE -> ... -> COMPLETE -> IDLE
    def t3_alarm(sm):
        sm.alarm = True

    def t3_center(sm):
        sm.detection = FakeDetection(True, 0.90, 0.50, 0.5, 'fire')

    def t3_close(sm):
        sm.ultrasonic_cm = 40.0

    sm = run_test('Full scenario: alarm -> extinguish -> back to IDLE', [
        ('Trigger alarm',
         t3_alarm, 0.5,
         lambda sm: sm.state == State.SEARCHING),
        ('Fire detected off-center (rotating)',
         lambda sm: setattr(sm, 'detection', FakeDetection(True, 0.9, 0.7, 0.5, 'fire')),
         1.0, lambda sm: sm.state == State.SEARCHING),
        ('Fire centered',
         t3_center, 0.5,
         lambda sm: sm.state == State.APPROACHING),
        ('Ultrasonic says close enough',
         t3_close, 0.5,
         lambda sm: sm.state == State.WARNING),
        ('Warning countdown (5 seconds)',
         None, 6.0,
         lambda sm: sm.state == State.EXTINGUISHING),
        ('Extinguisher discharge (~8 seconds)',
         None, 9.0,
         lambda sm: sm.state == State.COMPLETE),
        ('Clear detection + return to IDLE',
         lambda sm: (setattr(sm, 'detection', FakeDetection()),
                     setattr(sm, 'ultrasonic_cm', 999.0)),
         4.0, lambda sm: sm.state == State.IDLE),
    ])
    if sm.state != State.IDLE:
        all_pass = False

    # Test 4: Search timeout
    sm = run_test('Search timeout returns to IDLE', [
        ('Trigger alarm, no fire visible',
         lambda sm: setattr(sm, 'alarm', True),
         0.5, lambda sm: sm.state == State.SEARCHING),
        ('Override timeout to 2s for quick test',
         lambda sm: setattr(sm, 'search_timeout', 2.0),
         3.0, lambda sm: sm.state == State.IDLE),
    ])
    if sm.state != State.IDLE:
        all_pass = False

    print(f'\n{"=" * 50}')
    if all_pass:
        print('  ALL TESTS PASSED')
    else:
        print('  SOME TESTS FAILED')
    print(f'{"=" * 50}\n')

    sys.exit(0 if all_pass else 1)


if __name__ == '__main__':
    main()
