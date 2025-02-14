import tkinter as tk
from tkinter import ttk, messagebox
import ITLA_reference as itla
import time

# Speed of light constant
C = 299792458  # m/s

class LaserControlApp:
    def __init__(self, master):
        self.master = master
        self.master.title("Pure Photonics Laser Control")
        self.master.geometry("600x500")

        # Connection and mode state
        self.sercon = None
        self.laser_enabled = False
        self.whisper_mode = False

        # --- Create GUI Components ---
        # Top frame for controls
        control_frame = ttk.Frame(master)
        control_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)

        ttk.Button(control_frame, text="Connect Laser", command=self.connect_laser).grid(row=0, column=0, padx=5, pady=5)
        self.enable_button = ttk.Button(control_frame, text="Enable Laser", command=self.toggle_laser)
        self.enable_button.grid(row=0, column=1, padx=5, pady=5)
        self.whisper_button = ttk.Button(control_frame, text="Enable Whisper Mode", command=self.toggle_whisper)
        self.whisper_button.grid(row=0, column=2, padx=5, pady=5)

        # Frequency settings frame
        freq_frame = ttk.LabelFrame(master, text="Frequency Settings")
        freq_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)

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

        # Current frequency display
        self.current_freq_label = ttk.Label(master, text="Current Frequency: ---")
        self.current_freq_label.pack(pady=10)

        # Message feed (scrolling terminal)
        msg_frame = ttk.LabelFrame(master, text="Status Messages")
        msg_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.message_feed = tk.Text(msg_frame, wrap="word", height=10)
        self.message_feed.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar = ttk.Scrollbar(msg_frame, orient="vertical", command=self.message_feed.yview)
        scrollbar.pack(side=tk.RIGHT, fill="y")
        self.message_feed.configure(yscrollcommand=scrollbar.set)

        # Start periodic update for frequency readout
        self.update_frequency()

    def connect_laser(self):
        self.sercon = itla.ITLAConnect('com5', 9600)
        if isinstance(self.sercon, int):
            self.update_message(f"Failed to connect to laser. Error code: {self.sercon}")
        else:
            self.update_message(f"Laser connected: {self.sercon}")

    def toggle_laser(self):
        if not self.sercon:
            messagebox.showerror("Error", "Laser not connected!")
            return

        if self.laser_enabled:
            result = itla.ITLA(self.sercon, 0x32, 0, 1)  # Write 0 to disable
            self.laser_enabled = False
            self.enable_button.config(text="Enable Laser")
            self.update_message("Laser disabled. You may now adjust frequency settings.")
        else:
            result = itla.ITLA(self.sercon, 0x32, 1, 1)  # Write 1 to enable
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
            result = itla.ITLA(self.sercon, 0x90, 0, 1)  # Write 0 to set dither mode
            self.whisper_mode = False
            self.whisper_button.config(text="Enable Whisper Mode")
            self.update_message("Switched to dither mode.")
        else:
            result = itla.ITLA(self.sercon, 0x90, 2, 1)  # Write 2 to enable whisper mode
            self.whisper_mode = True
            self.whisper_button.config(text="Disable Whisper Mode")
            self.update_message("Whisper mode enabled.")

    def set_initial_frequency(self):
        if self.laser_enabled:
            messagebox.showwarning("Warning", "Please disable the laser before adjusting frequency!")
            return

        wavelength = self.wavelength_var.get()  # in nm
        freq_hz = C / (wavelength * 1e-9)
        freq_thz = freq_hz / 1e12  # in THz

        int_thz = int(freq_thz)
        frac_thz = freq_thz - int_thz
        # Here we assume register 0x36 takes values in 0.1 GHz units.
        # 1 THz = 1000 GHz, so 0.1 GHz = 0.0001 THz.
        frac_value = int(round(frac_thz / 0.0001))

        res1 = itla.ITLA(self.sercon, 0x35, int_thz, 1)
        res2 = itla.ITLA(self.sercon, 0x36, frac_value, 1)
        self.update_message(f"Initial frequency set: {int_thz} THz + {frac_value} (0.1GHz units) → {freq_thz:.6f} THz")

    def apply_ftf_offset(self):
        if self.laser_enabled:
            messagebox.showwarning("Warning", "Disable the laser before adjusting frequency!")
            return

        offset_mhz = self.ftf_offset_var.get()
        res = itla.ITLA(self.sercon, 0x62, int(offset_mhz), 1)
        self.update_message(f"FTF offset set to {offset_mhz} MHz. This offset is applied to the laser output frequency in real time.")

    def update_frequency(self):
        if self.sercon:
            freq_thz = itla.ITLA(self.sercon, 0x40, 0, 0)
            frac_0_1mhz = itla.ITLA(self.sercon, 0x41, 0, 0)  # Each unit = 0.1 MHz
            fine_mhz = itla.ITLA(self.sercon, 0x68, 0, 0)       # in MHz
            total_freq_mhz = (freq_thz * 1e6) + (frac_0_1mhz * 0.1) + fine_mhz
            total_freq_thz = total_freq_mhz / 1e6
            self.current_freq_label.config(text=f"Current Frequency: {total_freq_thz:.6f} THz")
        self.master.after(500, self.update_frequency)

    def update_message(self, msg):
        timestamp = time.strftime("[%H:%M:%S] ")
        self.message_feed.insert(tk.END, timestamp + msg + "\n")
        self.message_feed.see(tk.END)

if __name__ == "__main__":
    root = tk.Tk()
    app = LaserControlApp(root)
    root.mainloop()
