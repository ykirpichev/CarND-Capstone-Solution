#!/usr/bin/env python

import time
import rospy
from std_msgs.msg import Bool, Float32
from dbw_mkz_msgs.msg import ThrottleCmd, SteeringCmd, BrakeCmd, SteeringReport
from geometry_msgs.msg import TwistStamped
import math

from twist_controller import Controller

'''
You can build this node only after you have built (or partially built) the `waypoint_updater` node.

You will subscribe to `/twist_cmd` message which provides the proposed linear and angular velocities.
You can subscribe to any other message that you find important or refer to the document for list
of messages subscribed to by the reference implementation of this node.

One thing to keep in mind while building this node and the `twist_controller` class is the status
of `dbw_enabled`. While in the simulator, its enabled all the time, in the real car, that will
not be the case. This may cause your PID controller to accumulate error because the car could
temporarily be driven by a human instead of your controller.

We have provided two launch files with this node. Vehicle specific values (like vehicle_mass,
wheel_base) etc should not be altered in these files.

We have also provided some reference implementations for PID controller and other utility classes.
You are free to use them or build your own.

Once you have the proposed throttle, brake, and steer values, publish it on the various publishers
that we have created in the `__init__` function.

'''

class DBWNode(object):
    def __init__(self):
        rospy.init_node('dbw_node')

        #vehicle_mass = rospy.get_param('~vehicle_mass', 1080.)#1736.35)
        vehicle_mass = rospy.get_param('~vehicle_mass', 1736.35)
        fuel_capacity = rospy.get_param('~fuel_capacity', 13.5)
        brake_deadband = rospy.get_param('~brake_deadband', .1)
        decel_limit = rospy.get_param('~decel_limit', -5)
        accel_limit = rospy.get_param('~accel_limit', 1.)
        #wheel_radius = rospy.get_param('~wheel_radius', 0.335)#0.2413)
        wheel_radius = rospy.get_param('~wheel_radius', 0.2413)
        wheel_base = rospy.get_param('~wheel_base', 2.8498)
        steer_ratio = rospy.get_param('~steer_ratio', 14.8)
        max_lat_accel = rospy.get_param('~max_lat_accel', 3.)
        max_steer_angle = rospy.get_param('~max_steer_angle', 8.)

        self.prev_time = -1
        self.dt = 0.02

        self.current_linear_v = 0
        self.goal_linear_v = 0
        self.goal_angular_v =0
        self.dbw_enabled = False
        self.stop_a = -1

        self.steer_pub = rospy.Publisher('/vehicle/steering_cmd',
                                         SteeringCmd, queue_size=1)
        self.throttle_pub = rospy.Publisher('/vehicle/throttle_cmd',
                                            ThrottleCmd, queue_size=1)
        self.brake_pub = rospy.Publisher('/vehicle/brake_cmd',
                                         BrakeCmd, queue_size=1)

        self.controller = Controller(self.dbw_enabled,
                                    vehicle_mass, fuel_capacity,
                                    brake_deadband, decel_limit,
                                    accel_limit, wheel_radius,
                                    wheel_base, steer_ratio,
                                    max_lat_accel, max_steer_angle)

        rospy.Subscriber('/current_velocity', TwistStamped, self.velocity_cb)
        rospy.Subscriber('/twist_cmd', TwistStamped, self.twist_cb)
        rospy.Subscriber('/vehicle/dbw_enabled', Bool, self.dbw_cb)
        rospy.Subscriber('/stop_a', Float32, self.stopa_cb)

        self.loop()

    def velocity_cb(self, msg):
        rospy.loginfo("velocity_cb is called")
        self.current_linear_v = msg.twist.linear.x

    def twist_cb(self, msg):
        rospy.loginfo("twist_cb is called")
        self.goal_linear_v = msg.twist.linear.x
        self.goal_angular_v = msg.twist.angular.z

    def dbw_cb(self, msg):
        rospy.loginfo("dbw_cb is called")
        self.dbw_enabled = msg.data

    def stopa_cb(self, msg):
        rospy.loginfo("stopa_cb is called")
        self.stop_a = msg.data

    def loop(self):
        rate = rospy.Rate(50) # 50Hz
        while not rospy.is_shutdown():
            if self.prev_time != -1:
                cur_time = time.time()
                self.dt = cur_time - self.prev_time
                self.prev_time = cur_time
            else:
                self.prev_time = time.time()

            if self.dbw_enabled:
                throttle, brake, steer = self.controller.control(self.dbw_enabled,
                                                                 self.goal_linear_v,
                                                                 self.goal_angular_v,
                                                                 self.stop_a,
                                                                 self.current_linear_v,
                                                                 self.dt)
                self.publish(throttle, brake, steer)

            rate.sleep()

    def publish(self, throttle, brake, steer):
        tcmd = ThrottleCmd()
        tcmd.enable = True
        tcmd.pedal_cmd_type = ThrottleCmd.CMD_PERCENT
        tcmd.pedal_cmd = throttle
        self.throttle_pub.publish(tcmd)

        scmd = SteeringCmd()
        scmd.enable = True
        scmd.steering_wheel_angle_cmd = steer
        self.steer_pub.publish(scmd)

        bcmd = BrakeCmd()
        bcmd.enable = True
        bcmd.pedal_cmd_type = BrakeCmd.CMD_TORQUE
        bcmd.pedal_cmd = brake
        self.brake_pub.publish(bcmd)


if __name__ == '__main__':
    DBWNode()
