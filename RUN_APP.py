# -*- coding: utf-8 -*-
"""
ตัวเปิดแอป Stock Advisor
========================
รันด้วยคำสั่ง:  python RUN_APP.py

ครั้งแรกจะติดตั้งไลบรารีให้อัตโนมัติ ใช้เวลาประมาณ 2-3 นาที
ครั้งถัดไปจะเปิดภายในไม่กี่วินาที
หน้าต่างนี้ต้องเปิดค้างไว้ตลอดเวลาที่ใช้งานแอป
"""
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
VENV = os.path.join(HERE, ".venv")


def venv_python():
    """หาไฟล์ python ใน venv — ต้องเรียกหลังสร้าง venv แล้วเท่านั้น"""
    for rel in (("Scripts", "python.exe"), ("bin", "python3"), ("bin", "python")):
        p = os.path.join(VENV, *rel)
        if os.path.exists(p):
            return p
    return None


def hold(code=1):
    print()
    try:
        input("กด Enter เพื่อปิดหน้าต่างนี้...")
    except EOFError:
        time.sleep(30)
    sys.exit(code)


def run(cmd):
    print("   >", os.path.basename(str(cmd[0])), " ".join(str(c) for c in cmd[1:4]), "...")
    return subprocess.call(cmd, cwd=HERE)


def main():
    os.chdir(HERE)
    print("=" * 62)
    print("  Stock Advisor  -  ระบบแนะนำหุ้นตามระดับความเสี่ยง")
    print("=" * 62)
    print()
    print(f"[1/3] Python {sys.version.split()[0]}")

    if sys.version_info < (3, 9):
        print("\n   ต้องใช้ Python 3.9 ขึ้นไป")
        hold()

    # สร้าง venv ถ้ายังไม่มี
    vpy = venv_python()
    if vpy is None:
        print("\n[2/3] กำลังสร้างสภาพแวดล้อม ...")
        if run([sys.executable, "-m", "venv", ".venv"]) != 0:
            print("\n   สร้าง virtual environment ไม่สำเร็จ")
            hold()
        vpy = venv_python()
        if vpy is None:
            print("\n   สร้าง venv แล้วแต่หาไฟล์ python ข้างในไม่เจอ")
            print("   ลองลบโฟลเดอร์ .venv แล้วรันใหม่อีกครั้ง")
            hold()
    else:
        print("\n[2/3] พบสภาพแวดล้อมเดิมแล้ว")

    # เช็คว่าไลบรารีใช้งานได้จริง ไม่ใช่แค่มีโฟลเดอร์ .venv
    ready = subprocess.call([vpy, "-c", "import streamlit, pandas, plotly"],
                            cwd=HERE,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL) == 0
    if ready:
        print("      ไลบรารีครบแล้ว ข้ามขั้นตอนติดตั้ง")
    else:
        print("      กำลังติดตั้ง streamlit, pandas, plotly ...")
        print("      ใช้เวลาประมาณ 2-3 นาที กรุณารอ อย่าปิดหน้าต่าง")
        run([vpy, "-m", "pip", "install", "--upgrade", "pip",
             "--quiet", "--disable-pip-version-check"])
        if run([vpy, "-m", "pip", "install", "-r", "requirements.txt",
                "--disable-pip-version-check"]) != 0:
            print("\n   ติดตั้งไลบรารีไม่สำเร็จ ตรวจสอบอินเทอร์เน็ตแล้วลองใหม่")
            hold()

    print("\n[3/3] กำลังเปิดแอป ...")
    print("      เบราว์เซอร์จะเปิดที่  http://localhost:8501")
    print("      ** เปิดหน้าต่างนี้ค้างไว้ตลอดเวลาที่นำเสนอ **")
    print("      กด Ctrl+C ที่หน้าต่างนี้เพื่อหยุดแอป")
    print()
    try:
        subprocess.call([vpy, "-m", "streamlit", "run", "app.py"], cwd=HERE)
    except KeyboardInterrupt:
        print("\nปิดแอปแล้ว")
    hold(0)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\nเกิดข้อผิดพลาด: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        hold()
