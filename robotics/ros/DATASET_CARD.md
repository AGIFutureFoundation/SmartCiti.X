---
license: other
license_name: to be decided by the owner
pretty_name: SmartCiti.X SCRIPTED robotics episodes as ROS 2 MCAP
task_categories:
  - robotics
tags:
  - ros2
  - mcap
  - rosbag2
  - synthetic
  - simulation
  - scripted
size_categories:
  - n<1K
annotations_creators:
  - machine-generated
source_datasets:
  - original
language:
  - en
configs:
  - config_name: default
    data_files:
      - split: train
        path: train/**/*.mcap
      - split: test
        path: test/**/*.mcap
dataset_info:
  record: ros-export/1
  provenance: SCRIPTED
  files: 520
  messages: 543708
  trained_models: 0
---

> **Not for publication: do not upload or share this dataset until the owner sets its licence.**

# SmartCiti.X SCRIPTED robotics episodes as ROS 2 MCAP (ros-export/1 card, tc-dataset/1 sections)

<!-- section:motivation -->
## Motivation
- Simulated robot episodes in the file format ROS 2 tools read: MCAP files with message encoding `cdr`, schema encoding `ros2msg` and the `ros2` profile, using standard message types (geometry_msgs/Twist, geometry_msgs/PoseStamped, nav_msgs/Odometry, sensor_msgs/JointState, std_msgs/String). They let a robotics team exercise a data pipeline, a bag reader or a loader on small, fully labelled, reproducible data.
- This card says what the files are and are not. It makes no claim about any use beyond that.

<!-- section:composition -->
## Composition
- 520 files, 543708 messages, 124888 time steps sampled at 5 Hz of simulation time. Total 159908805 bytes uncompressed (152.5 MiB; largest file 391.7 KiB, smallest 103.7 KiB); chunk compression is off by default.
- By source policy: scripted 260, greedy 260. By task: litter-pickup 120, litter-sort 160, rov-survey 120, gate-drive 120. One file per policy x task x curriculum level x seed.
- Splits (the model arena's own, robotics/arena/registry/models.json): TRAIN seeds 1-10 = 260 files, TEST seeds 11-20 = 260 files. A file sits in the folder of its seed's split and in no other; a TEST seed never appears in a TRAIN file. The Omega Claw JSONL has its own seed splits (train 1-16, val 17-18, test 19-20); do not mix the two schemes.
- 257 of 520 episodes met their task's success rule; the rest are kept and labelled in each file's metadata, not filtered.
- Topics in each file:
  - `/instruction` (std_msgs/msg/String) - the quoted task instruction (robotics/claw dataset); one message at t=0
  - `/cmd_vel` (geometry_msgs/msg/Twist) - the action: linear.x = v, angular.z = w; for the ROV linear.z = -vz; one per sample
  - `/odom` (nav_msgs/msg/Odometry) - exact simulated pose and body-frame velocity (covariances 0 = exact; there is no sensor noise); one per sample
  - `/sim/ground_truth/pose` (geometry_msgs/msg/PoseStamped) - the same simulated pose in the map frame; one per sample
  - `/joint_states` (sensor_msgs/msg/JointState) - SCHEMATIC drive degrees of freedom: velocity of drive_linear (m/s) and drive_yaw (rad/s); there is no joint model; one per sample
  - `/gripper_command` (sensor_msgs/msg/JointState) - the commanded gripper value (0 open, 1 close; the simulator closes at 0.5 or more); the arm has no joint model; one per sample, litter-sort only
- Each file also holds one MCAP Metadata record, `smartcitix.episode` (policy, policy version, task, level, seed, split, outcome, trajectory hash, provenance, this card's limits), and one Attachment, `scene.json` (the seeded scene layout: obstacles, items, gates, bin, targets).
- Time: simulation seconds since the episode start (sample step index x dt_s); not wall-clock time. Message log time, publish time and header stamps agree.

<!-- section:collection -->
## Collection process
- Provenance SCRIPTED. Each episode is produced headless by the page simulator's own SIM_CORE (web/robokit.py) driven by a hand-written policy: the SCRIPTED reference (the Omega Claw dataset's 260 samples; policy version f2fd6b4610679ad9) or the SCRIPTED greedy heuristic (robotics/arena/policies.js). Deterministic: a rebuild reproduces every byte.
- Robots (a wheeled rover, an arm on a base, a survey ROV) and the arenas are AUTHORED and SCHEMATIC. The instruction text of every file is quoted from a registry and is the same for both policies on the same task.
- Nothing was recorded from a real machine or a person. No learner data was read.

<!-- section:preprocessing -->
## Preprocessing
- Frames and signs (PROPOSED mapping, checked against the simulator's own update rule in the suite): the simulator's east/north metres become x/y of a local east-north-up frame (REP 103: X east, Y north, Z up; yaw zero pointing east, counter-clockwise positive); its heading (0 = north, positive toward west) becomes yaw about z with yaw_ros = yaw + pi/2; v is linear.x and w is angular.z; the ROV's depth (positive down) becomes z = -depth and vz becomes linear.z = -vz. The origin is the start point, not a geographic location.
- Odometry covariances are 0: the simulated pose is exact. Wheel joints, gripper state and `near` ids are not exported (no joint model; `near` is in the Omega Claw JSONL).
- The ros2msg schema text of every channel is the ROS 2 jazzy .msg files byte for byte (ros2/common_interfaces at a941f14bb318d8d904505ed935ccbb97f24a70a4, ros2/rcl_interfaces at 7aa3caf43377ea6ad615bc1040832e2c7566bfbe, Apache-2.0), joined the way rosbag2 joins them. CDR is XCDR1 little endian.
- Every check is in robotics/ros/test.mjs: magic bytes, header, footer, summary and indexes, CRCs, schema text, message counts against the source episodes, monotonic timestamps, no TEST seed in a TRAIN file, and this card's counts.

<!-- section:uses -->
## Uses
- Intended use: testing bag readers, loaders, message-type handling and training-pipeline plumbing on synthetic data.
- NOT real robot data. NOT recorded from any robot, vehicle, ROV or person. NOT learner data. NOT the output of a trained model: trained_models is 0 for this pack.
- Sim-to-real gap: Large and unmeasured. The simulator is a unicycle on a flat arena with circle obstacles: no wheels, tyres or friction, no mass or inertia, no actuator dynamics (the commanded velocity, clamped to the limits, is applied in full at the next step), no latency, no sensor model or noise (odometry is exact, covariances are 0), no camera, lidar or IMU, no joints for the arm (a gripper flag), no buoyancy, current model or tether for the ROV. A policy fitted to these messages has not been shown to work on any real machine.
- Nothing in this export sends a command to a real robot or device. /cmd_vel here is a recorded simulated action. Replaying these files into a live ROS graph is outside this repository and would need a named human operator and the repository's safety gate; this export provides no path to hardware.
- Conformance: Container and encoding follow the MCAP specification and the MCAP ros2 profile text, and the message definitions are the ROS 2 jazzy files byte for byte. Every file was read back, with checksums validated, by three independent open-source readers: the Python package mcap (with mcap-ros2-support decoding the messages), the Python package rosbags, and the npm package @mcap/core (used for validation only; the repository depends on none of them). No ROS 2 installation was available to the authors, so playback with ros2 bag play is unverified.
- Not written: The bag directory metadata.yaml of rosbag2 is not written, and the channel metadata key topic_type_hash is omitted (it needs the ROS type-description tooling). offered_qos_profiles holds AUTHORED defaults, not QoS recorded from a live graph.

<!-- section:distribution -->
## Distribution
- Not for publication: do not upload or share this dataset until the owner sets its licence.
- Licence: to be decided by the owner. Until the owner decides, this card grants no licence; the vendored ROS message definitions stay under their own Apache-2.0 licence (robotics/ros/msgs/LICENSE).
- Nothing is uploaded or hosted by this repository: robotics/ros/export.mjs writes the files where it is run (`node robotics/ros/export.mjs --out <dir>`, optional `--zstd` chunk compression).

<!-- section:maintenance -->
## Maintenance
- Digest of all file hashes: 67bab648bd677090. The registry robotics/ros/registry/ros.json stores every file's size and sha256; `python3 robotics/ros/build.py --check` fails when it is stale.
- Known gaps: no image, lidar, IMU or point-cloud topics; one embodiment per task; two policies; 520 episodes.
