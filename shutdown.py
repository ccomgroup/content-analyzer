import os
import signal
import psutil
import sys

def find_streamlit_process():
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            # Check if this is a Python process
            if proc.info['name'] == 'python.exe':
                cmdline = proc.info['cmdline']
                if cmdline and any('streamlit' in arg.lower() for arg in cmdline):
                    return proc.pid
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return None

def shutdown_streamlit():
    pid = find_streamlit_process()
    if pid:
        try:
            # Try to terminate the process gracefully first
            os.kill(pid, signal.SIGTERM)
            print(f"Terminated Streamlit process (PID: {pid})")
        except Exception as e:
            print(f"Error terminating process: {e}")
            try:
                # If graceful termination fails, force kill the process
                os.kill(pid, signal.SIGKILL)
                print(f"Force killed Streamlit process (PID: {pid})")
            except Exception as e:
                print(f"Error force killing process: {e}")
    else:
        print("No Streamlit process found")

if __name__ == "__main__":
    shutdown_streamlit()
