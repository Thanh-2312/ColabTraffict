#!/usr/bin/env python3
"""
==============================================================================
AUTOMATED TEST SUITE RUNNER FOR TRAFFIC CONTROLLERS & EDGE CASES
==============================================================================
Thực thi kiểm thử tự động toàn bộ Unit Tests và Edge Cases cho:
  - Base Model & IDM Kinematics (Graph, Anti-overlap spawn, Liveness)
  - Fixed-Time Controller (Phases, Durations, Independence)
  - MaxPressure Controller (Pressure Math, Min/Max Green, Hysteresis Rule, Anti-Flicker)
  - Q-Learning Controller (State Encoding, Bellman Equation, Epsilon Floor, Extreme Reward)
==============================================================================
"""

import os
import sys
import subprocess
import re
import time

GAMA_HEADLESS = "/Applications/Gama.app/Contents/headless/gama-headless.sh"
BASE_DIR = "/Users/mac/Documents/GAMA"
TEST_MODEL = os.path.join(BASE_DIR, "Traffic/models/test_traffic_controllers.gaml")

def run_test_suite():
    print("=" * 90)
    print("🧪 BẮT ĐẦU CHẠY BỘ TEST SUITE: UNIT TESTS & EDGE CASES KIỂM CHỨNG GAMA")
    print("=" * 90)
    
    cmd = [
        "bash", GAMA_HEADLESS,
        "-batch", "my_batch_experiment",
        TEST_MODEL
    ]
    
    start_time = time.time()
    process = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, bufsize=1
    )
    
    test_results = []
    pattern = re.compile(r"TEST_RESULT,([^,]+),([^,]+),([^,]+),(.*)")
    
    print("\n🚀 Đang thực thi mô phỏng và thu thập các assertions...\n")
    
    for line in iter(process.stdout.readline, ''):
        line = line.strip()
        match = pattern.search(line)
        if match:
            suite = match.group(1).strip()
            test_id = match.group(2).strip()
            status = match.group(3).strip()
            message = match.group(4).strip()
            
            icon = "✅" if status == "PASS" else "❌"
            print(f"  {icon} [{status}] {suite:12s} | {test_id:30s} | {message}")
            
            test_results.append({
                "suite": suite,
                "test_id": test_id,
                "status": status,
                "message": message
            })
            
    process.wait()
    duration = time.time() - start_time
    
    # Summary report
    print("\n" + "=" * 90)
    print(f"📊 BẢNG TỔNG KẾT KẾT QUẢ KIỂM THỬ TOÀN DIỆN (Thời gian chạy: {duration:.1f}s)")
    print("=" * 90)
    print(f"{'Module / Suite':<16} | {'Mã Test Case':<32} | {'Trạng thái':<10} | {'Chi tiết'}")
    print("-" * 90)
    
    passed_count = sum(1 for t in test_results if t['status'] == 'PASS')
    failed_count = sum(1 for t in test_results if t['status'] == 'FAIL')
    total_count = len(test_results)
    
    for t in test_results:
        st_color = "PASS" if t['status'] == 'PASS' else "FAIL"
        print(f"{t['suite']:<16} | {t['test_id']:<32} | {st_color:<10} | {t['message']}")
        
    print("=" * 90)
    print(f"📈 TỔNG KẾT: Đã hoàn thành {total_count} Test Cases.")
    print(f"   - ĐẠT (PASS) : {passed_count} / {total_count} ({passed_count/total_count*100.0:.1f}%)" if total_count > 0 else "0")
    print(f"   - HỎNG (FAIL): {failed_count} / {total_count}")
    
    if failed_count == 0 and total_count > 0:
        print("\n🎉 XÁC NHẬN: 100% TẤT CẢ UNIT TESTS & EDGE CASES ĐỀU ĐẠT CHUẨN XUẤT SẮC!")
    else:
        print("\n⚠️ CẢNH BÁO: CÓ TEST CASE BỊ LỖI, VUI LÒNG KIỂM TRA LẠI LOG CHI TIẾT!")
    print("=" * 90 + "\n")

if __name__ == "__main__":
    run_test_suite()
