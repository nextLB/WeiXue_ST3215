import time
import sys
import os

from scservo_sdk import *

# ===================== 全局配置 =====================
# 模式选择（你后面自己改这里测试）：
#   0 = 位置模式（伺服/角度控制）
#   1 = 速度模式（轮子/连续旋转）
SERVO_MODE = 0

SCS_ID       = 1
BAUDRATE     = 1000000
DEVICENAME   = 'COM14'

# 寄存器地址（来自官方内存表）
ADDR_MODE            = 33   # SMS_STS_MODE
ADDR_TORQUE_ENABLE   = 40   # 扭矩使能
ADDR_GOAL_POSITION_L = 42   # 目标位置低位
ADDR_GOAL_SPEED_L    = 46   # 目标速度低位
ADDR_ACC             = 41   # 加速度

# 位置模式参数（可根据机械结构修改）
POS_MIN = 0        # 最小位置（0~4095）
POS_MAX = 4095     # 最大位置
DEFAULT_SPEED = 1500
DEFAULT_ACC   = 50
# ==================================================


def init_port():
    """初始化串口并返回 portHandler 和 packetHandler"""
    portHandler = PortHandler(DEVICENAME)
    packetHandler = sms_sts(portHandler)

    if not portHandler.openPort():
        print("Failed to open the port")
        sys.exit(1)
    if not portHandler.setBaudRate(BAUDRATE):
        print("Failed to change the baudrate")
        portHandler.closePort()
        sys.exit(1)

    print(f"Port {DEVICENAME} opened, baudrate {BAUDRATE}")
    return portHandler, packetHandler


def set_servo_mode(packetHandler, mode):
    """
    切换舵机模式
    mode = 0 → 位置模式
    mode = 1 → 速度模式（轮模式）
    """
    # 切换模式前先关闭扭矩，避免模式冲突
    packetHandler.write1ByteTxRx(SCS_ID, ADDR_TORQUE_ENABLE, 0)
    time.sleep(0.05)

    comm, err = packetHandler.write1ByteTxRx(SCS_ID, ADDR_MODE, mode)
    if comm != COMM_SUCCESS:
        print("模式切换失败:", packetHandler.getTxRxResult(comm))
        return False
    if err != 0:
        print("模式切换错误:", packetHandler.getRxPacketError(err))
        return False

    # 重新使能扭矩
    packetHandler.write1ByteTxRx(SCS_ID, ADDR_TORQUE_ENABLE, 1)
    time.sleep(0.05)

    mode_name = "位置模式 (Mode 0)" if mode == 0 else "速度模式 (Mode 1)"
    print(f"已切换到: {mode_name}")
    return True


def control_speed(packetHandler, target_speed, duration=1.0):
    """
    速度模式控制函数（在循环中调用）
    :param target_speed: 目标速度，正数正转，负数反转，0 停止
                         范围约 -32767 ~ 32767
    :param duration:     旋转时间（秒），到时间后自动停止
    """
    # 写目标速度（速度模式使用 GOAL_SPEED 寄存器）
    speed = int(target_speed) & 0xFFFF  # 转为无符号16位，底层处理正负
    comm, err = packetHandler.write2ByteTxRx(SCS_ID, ADDR_GOAL_SPEED_L, speed)
    if comm != COMM_SUCCESS:
        print("写速度失败:", packetHandler.getTxRxResult(comm))
        return
    if err != 0:
        print("写速度错误:", packetHandler.getRxPacketError(err))
        return

    if target_speed != 0 and duration > 0:
        time.sleep(duration)
        # 到时停止
        packetHandler.write2ByteTxRx(SCS_ID, ADDR_GOAL_SPEED_L, 0)

def deg_to_pos(angle):
    return int(angle * 4096 / 360) % 4096

def control_position(packetHandler, target_position, speed=DEFAULT_SPEED, acc=DEFAULT_ACC):
    """
    位置模式控制函数（在循环中调用）
    :param target_position: 目标位置（0~4095，对应 0~360°）
                             例如 2048 ≈ 180° 中位
    :param speed: 运动速度（步/秒）
    :param acc:   加速度
    """
    # 限幅
    pos = max(POS_MIN, min(POS_MAX, int(target_position)))

    # WritePosEx 是官方封装好的位置写入函数：位置 + 速度 + 加速度
    comm, err = packetHandler.WritePosEx(SCS_ID, pos, speed, acc)
    if comm != COMM_SUCCESS:
        print("写位置失败:", packetHandler.getTxRxResult(comm))
    if err != 0:
        print("写位置错误:", packetHandler.getRxPacketError(err))


def main():
    portHandler, packetHandler = init_port()

    # ===== 根据全局变量切换模式 =====
    if not set_servo_mode(packetHandler, SERVO_MODE):
        portHandler.closePort()
        return

    try:
        if SERVO_MODE == 1:
            # -------- 速度模式测试 --------
            # 正转 2 秒
            control_speed(packetHandler, 3072, duration=2.0)
            time.sleep(0.5)

            # 反转 2 秒
            control_speed(packetHandler, -3072, duration=2.0)
            time.sleep(0.5)

            # 停止
            control_speed(packetHandler, 0)

        else:
            # -------- 位置模式测试 --------
            # 转到 1024（约 90°）
            control_position(packetHandler, deg_to_pos(90))
            time.sleep(2.0)

            # 转到 3072（约 270°）(旋转速度更快)
            control_position(packetHandler, deg_to_pos(270), speed=3072)
            time.sleep(2.0)

            # 回到中位 2048（约 180°）（加速度更大）
            control_position(packetHandler, deg_to_pos(180), speed=1000, acc=254)
            time.sleep(2.0)

    finally:
        # 退出前确保舵机停止
        if SERVO_MODE == 1:
            control_speed(packetHandler, 0)
        portHandler.closePort()
        print("串口已关闭，程序结束")


if __name__ == "__main__":
    main()