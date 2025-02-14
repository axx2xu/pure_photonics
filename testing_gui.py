import tkinter as tk
from tkinter import ttk, messagebox
import ITLA_reference as itla
import time
import threading

# Speed of light constant
C = 299792458  # m/s

class LaserControlApp:
    def __init__(self, master):
        self.master = master
        self.master.title("Pure Photonics Laser Control")
        self.master.geometry("600x550")

        # Connection and mode state
        self.sercon = None
        self.laser_enabled = False
        self.whisper_mode = False
        self.frequency_thread_running = False

        # -------------------------------
        # COM Port Selection Frame
        # -------------------------------
        com_frame = ttk.LabelFrame(master, text="Connection")
        com_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)

        ttk.Label(com_frame, text="COM Port:").grid(row=0, column=0, sticky="e", padx=5, pady=5)
        self.com_port_var = tk.StringVar(value="COM5")
        self.com_entry = ttk.Entry(com_frame, textvariable=self.com_port_var, width=10)
        self.com_entry.grid(row=0, column=1, sticky="w", padx=5, pady=5)
        ttk.Button(com_frame, text="Connect Laser", command=self.connect_laser_threaded).grid(row=0, column=2, padx=5, pady=5)

        # -------------------------------
        # Top frame for Laser Controls
        # -------------------------------
        control_frame = ttk.Frame(master)
        control_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)

        self.enable_button = ttk.Button(control_frame, text="Enable Laser", command=self.toggle_laser)
        self.enable_button.grid(row=0, column=0, padx=5, pady=5)
        self.whisper_button = ttk.Button(control_frame, text="Enable Whisper Mode", command=self.toggle_whisper)
        self.whisper_button.grid(row=0, column=1, padx=5, pady=5)

        # -------------------------------
        # Frequency Settings Frame
        # -------------------------------
        freq_frame = ttk.LabelFrame(master, text="Frequency Settings")
        freq_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)

        ttk.Label(freq_frame, text="Initial Wavelength (nm):").grid(row=0, column=0, sticky="e", padx=5, pady=5)
        self.wavelength_var = tk.DoubleVar(value=1550)
        self.wavelength_entry = ttk.Entry(freq_frame, textvariable=self.wavelength_var, width=10)
        self.wavelength_entry.grid(row=0, column=1, sticky="w", padx=5, pady=5)
        self.set_initial_button = ttk.Button(freq_frame, text="Set Initial Frequency", command=self.set_initial_frequency)
        self.set_initial_button.grid(row=0, column=2, padx=5, pady=5)

        ttk.Label(freq_frame, text="FTF Offset (MHz):").grid(row=1, column=0, sticky="e", padx=5, pady=5)
        self.ftf_offset_var = tk.DoubleVar(value=0)
        self.ftf_offset_entry = ttk.Entry(freq_frame, textvariable=self.ftf_offset_var, width=10)
        self.ftf_offset_entry.grid(row=1, column=1, sticky="w", padx=5, pady=5)
        self.apply_ftf_button = ttk.Button(freq_frame, text="Apply FTF Offset", command=self.apply_ftf_offset)
        self.apply_ftf_button.grid(row=1, column=2, padx=5, pady=5)

        # -------------------------------
        # Current Frequency Display
        # -------------------------------
        self.current_freq_label = ttk.Label(master, text="Current Frequency: ---")
        self.current_freq_label.pack(pady=5)

        # -------------------------------
        # Message Feed (Scrolling Terminal)
        # -------------------------------
        msg_frame = ttk.LabelFrame(master, text="Status Messages")
        msg_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=5)
        self.message_feed = tk.Text(msg_frame, wrap="word", height=10)
        self.message_feed.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar = ttk.Scrollbar(msg_frame, orient="vertical", command=self.message_feed.yview)
        scrollbar.pack(side=tk.RIGHT, fill="y")
        self.message_feed.configure(yscrollcommand=scrollbar.set)

        # Start the frequency update thread
        self.start_frequency_thread()

    # ----------------------------------------
    # Connection Functions
    # ----------------------------------------
    def connect_laser_threaded(self):
        threading.Thread(target=self.connect_laser, daemon=True).start()

    def connect_laser(self):
        self.update_message("Attempting to connect to laser...")
        port = self.com_port_var.get().strip()
        self.sercon = itla.ITLAConnect(port, 9600)
        if isinstance(self.sercon, int):
            self.update_message(f"Failed to connect to laser on {port}. Error code: {self.sercon}")
        else:
            self.update_message(f"Laser connected on {port}: {self.sercon}")

    # ----------------------------------------
    # Laser Enable and Whisper Mode
    # ----------------------------------------
    def toggle_laser(self):
        if not self.sercon:
            messagebox.showerror("Error", "Laser not connected!")
            return

        if self.laser_enabled:
            itla.ITLA(self.sercon, 0x32, 0, 1)  # Write 0 to disable
            self.laser_enabled = False
            self.enable_button.config(text="Enable Laser")
            self.update_message("Laser disabled. You may now adjust frequency settings.")
        else:
            itla.ITLA(self.sercon, 0x32, 1, 1)  # Write 1 to enable
            self.laser_enabled = True
            self.enable_button.config(text="Disable Laser")
            self.update_message("Laser enabled. Frequency settings are locked; disable the laser to change them.")

    def toggle_whisper(self):
        if not self.sercon:
            messagebox.showerror("Error", "Laser not connected!")
            return
        if self.laser_enabled:
            messagebox.showwarning("Warning", "Please disable the laser before changing whisper mode!")
            return

        if self.whisper_mode:
            itla.ITLA(self.sercon, 0x90, 0, 1)  # Write 0 for dither mode
            self.whisper_mode = False
            self.whisper_button.config(text="Enable Whisper Mode")
            self.update_message("Switched to dither mode.")
        else:
            itla.ITLA(self.sercon, 0x90, 2, 1)  # Write 2 for whisper mode
            self.whisper_mode = True
            self.whisper_button.config(text="Disable Whisper Mode")
            self.update_message("Whisper mode enabled.")

    # ----------------------------------------
    # Frequency Setting Functions
    # ----------------------------------------
    def set_initial_frequency(self):
        if self.laser_enabled:
            messagebox.showwarning("Warning", "Please disable the laser before adjusting frequency!")
            return

        # Convert wavelength (nm) to frequency (Hz)
        wavelength = self.wavelength_var.get()  # in nm
        freq_hz = C / (wavelength * 1e-9)
        freq_thz = freq_hz / 1e12  # in THz

        # Split frequency into three parts for Device Settings:
        # 0x35: integer part (THz)
        int_thz = int(freq_thz)
        # 0x36: fractional part in 0.1 GHz units (each count = 0.0001 THz)
        frac_thz = freq_thz - int_thz
        GHz_frac_value = int(round(frac_thz*1e-4)) # convert to .1GHz units
        # 0x67: fine offset in MHz (each count = 1e-6 THz)
        base_set_thz = int_thz + (GHz_frac_value * 1e4)
        MHz_offset_thz = freq_thz - base_set_thz
        MHz_frac_value = int(round(MHz_offset_thz / 1e-6))

        # Write to registers (Device Settings)
        itla.ITLA(self.sercon, 0x35, int_thz, 1)
        itla.ITLA(self.sercon, 0x36, GHz_frac_value, 1)
        itla.ITLA(self.sercon, 0x67, MHz_frac_value, 1)
        self.update_message(
            f"Initial frequency set: {int_thz} THz + {GHz_frac_value} (0.1GHz units) + {MHz_frac_value} (MHz fine offset) → {freq_thz:.6f} THz"
        )

    def apply_ftf_offset(self):
        if self.laser_enabled:
            messagebox.showwarning("Warning", "Disable the laser before adjusting frequency!")
            return

        offset_mhz = self.ftf_offset_var.get()
        itla.ITLA(self.sercon, 0x62, int(offset_mhz), 1)
        self.update_message(f"FTF offset set to {offset_mhz} MHz. This offset is applied to the laser output frequency in real time.")

    # ----------------------------------------
    # Frequency Readback Loop
    # ----------------------------------------
    def frequency_update_loop(self):
            """
            Reads registers from Device Operating Information:
            0x40: Laser frequency (THz)
            0x41: Laser Frequency (0.1 MHz) [each count = 1e-7 THz]
            0x68: Laser Frequency (MHz) [each count = 1e-6 THz]
            The total frequency (in THz) is computed as:
            total = (0x40) + (0x41)*1e-7 + (0x68)*1e-6
            """
            while self.frequency_thread_running:
                if self.sercon:
                    try:
                        thz_int = itla.ITLA(self.sercon, 0x40, 0, 0)       # integer THz
                        frac_0_1mhz = itla.ITLA(self.sercon, 0x41, 0, 0)  # fractional part in 0.1 MHz increments
                        fine_mhz = itla.ITLA(self.sercon, 0x68, 0, 0)     # offset in MHz

                        total_freq_thz = thz_int + (frac_0_1mhz * 1e-7) + (fine_mhz * 1e-6)

                    except Exception as e:
                        total_freq_thz = 0
                        self.update_message(f"Error reading frequency: {e}")
                    self.master.after(0, lambda: self.current_freq_label.config(text=f"Current Frequency: {total_freq_thz:.6f} THz"))
                time.sleep(0.5)

    def start_frequency_thread(self):
        self.frequency_thread_running = True
        threading.Thread(target=self.frequency_update_loop, daemon=True).start()

    # ----------------------------------------
    # Message Logging
    # ----------------------------------------
    def update_message(self, msg):
        timestamp = time.strftime("[%H:%M:%S] ")
        self.message_feed.insert(tk.END, timestamp + msg + "\n")
        self.message_feed.see(tk.END)

# ------------------------------------------------------------------------------
# Main Entry
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    root = tk.Tk()
    app = LaserControlApp(root)
    root.mainloop()
