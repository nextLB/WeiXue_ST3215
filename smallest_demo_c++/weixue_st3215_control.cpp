#include <iostream>
#include <unistd.h> // 提供 usleep 和 sleep
#include "SCServo.h"

// ===================== 全局配置 =====================
// 模式选择：0 = 位置模式（角度控制）, 1 = 速度模式（连续旋转）
const int SERVO_MODE = 0; 

const u8  SERVO_ID  = 1;
const int BAUDRATE  = 1000000;
// 注意：如果通过命令行传参，这个宏可以不用；这里留作备用
const char* DEFAULT_DEVICE = "/dev/ttyACM0"; 

// 位置模式参数
const int POS_MIN = 0;
const int POS_MAX = 4095;
const int DEFAULT_SPEED = 1500;
const int DEFAULT_ACC   = 50;
const int MAX_ACC       = 254; // C++ SDK 里 acc 是 u8 类型，最大 254

// 实例化舵机对象
SMS_STS sm_st;

// ===================== 辅助函数 =====================

// 角度转编码器步数（0~360度 -> 0~4095）
int deg_to_pos(double angle) {
    return (int)(angle * 4096.0 / 360.0) % 4096;
}

// 切换舵机模式
void set_servo_mode(int mode) {
    sm_st.unLockEprom(SERVO_ID);
    if (mode == 1) {
        sm_st.WheelMode(SERVO_ID); // 速度模式（写入寄存器1）
        std::cout << "已切换到: 速度模式 (Mode 1)" << std::endl;
    } else {
        sm_st.writeByte(SERVO_ID, SMS_STS_MODE, 0); // 位置模式（写入寄存器0）
        std::cout << "已切换到: 位置模式 (Mode 0)" << std::endl;
    }
    sm_st.LockEprom(SERVO_ID);
    usleep(100000); // 等待 100ms 让底层生效
}

// 速度控制（带时间控制）
void control_speed(int target_speed, double duration_sec) {
    // 限制最大速度，防止误传超过物理极限
    if (target_speed > 3072) target_speed = 3072;
    if (target_speed < -3072) target_speed = -3072;

    // WriteSpe(舵机ID, 目标速度, 加速度)
    // 底层会自动处理负数的符号位
    sm_st.WriteSpe(SERVO_ID, target_speed, DEFAULT_ACC);
    
    if (target_speed != 0 && duration_sec > 0) {
        usleep((int)(duration_sec * 1000000)); // 延时指定秒数
        // 时间到，停止
        sm_st.WriteSpe(SERVO_ID, 0, DEFAULT_ACC);
    }
}

// 位置控制
void control_position(int target_pos, int speed = DEFAULT_SPEED, int acc = DEFAULT_ACC) {
    // 限幅
    if (target_pos < POS_MIN) target_pos = POS_MIN;
    if (target_pos > POS_MAX) target_pos = POS_MAX;
    if (acc > MAX_ACC) acc = MAX_ACC;
    
    // WritePosEx(舵机ID, 位置, 速度, 加速度)
    sm_st.WritePosEx(SERVO_ID, target_pos, speed, acc);
}

// ===================== 主函数 =====================
int main(int argc, char **argv) {
    const char* device_name = (argc >= 2) ? argv[1] : DEFAULT_DEVICE;

    std::cout << "Port: " << device_name << ", Baudrate: " << BAUDRATE << std::endl;
    if (!sm_st.begin(BAUDRATE, device_name)) {
        std::cout << "Failed to init sms/sts motor!" << std::endl;
        return 0;
    }

    // 初始化并切换模式
    set_servo_mode(SERVO_MODE);

    if (SERVO_MODE == 1) {
        // ================= 速度模式测试 =================
        std::cout << "--- 速度模式测试开始 ---" << std::endl;
        
        std::cout << "正转 3072 速度，持续 2 秒..." << std::endl;
        control_speed(3072, 2.0);
        usleep(500000); // 停 0.5 秒

        std::cout << "反转 -3072 速度，持续 2 秒..." << std::endl;
        control_speed(-3072, 2.0);
        usleep(500000);

        std::cout << "停止..." << std::endl;
        control_speed(0, 0);

    } else {
        // ================= 位置模式测试 =================
        std::cout << "--- 位置模式测试开始 ---" << std::endl;

        std::cout << "转到 90 度 (慢速柔和)..." << std::endl;
        control_position(deg_to_pos(90), 1500, 50);
        sleep(2); // 等待 2 秒

        std::cout << "转到 270 度 (满速猛冲)..." << std::endl;
        control_position(deg_to_pos(270), 3072, 254);
        sleep(2);

        std::cout << "回到 180 度 (中位)..." << std::endl;
        control_position(deg_to_pos(180), 1000, 254);
        sleep(2);
    }

    sm_st.end();
    std::cout << "串口已关闭，程序结束" << std::endl;
    return 1;
}