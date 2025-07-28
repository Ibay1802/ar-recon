import tkinter as tk
from tkinter import filedialog, messagebox, font
import subprocess
import threading

class FrontendApp:
    def __init__(self, root):
        self.root = root
        root.title("Backend Control Panel")
        root.geometry("450x750")
        root.configure(bg="#f5f7fa")
        root.resizable(False, False)
        self.center_window(450, 750)

        # Fonts
        self.title_font = font.Font(family="Segoe UI", size=16, weight="bold")
        self.btn_font = font.Font(family="Segoe UI", size=11)
        self.label_font = font.Font(family="Segoe UI", size=10)

        # Store paths for Data Accurate CSVs
        self.students_csv = None
        self.invoice_csv = None
        self.payment_csv = None

        # Title Label
        title_label = tk.Label(root, text="Backend Control Panel", font=self.title_font, bg="#f5f7fa", fg="#333")
        title_label.pack(pady=(20, 15))

        # Frame for Accurate Upload button + popup
        accurate_frame = tk.LabelFrame(root, text="Data Accurate Upload", padx=15, pady=15, bg="#ffffff", fg="#444", font=self.label_font)
        accurate_frame.pack(padx=20, pady=10, fill="x")

        upload_accurate_btn = tk.Button(accurate_frame, text="Upload Accurate CSV Files", command=self.open_accurate_upload_popup,
                                        font=self.btn_font, bg="#4a90e2", fg="white", activebackground="#357ABD", relief="flat", padx=10, pady=8)
        upload_accurate_btn.pack(fill="x")

        # Labels to show selected files for Data Accurate
        self.students_label = tk.Label(accurate_frame, text="Students CSV: None", bg="#ffffff", fg="#555", font=self.label_font, anchor="w")
        self.students_label.pack(fill="x", pady=(8, 0))
        self.invoice_label = tk.Label(accurate_frame, text="Invoice CSV: None", bg="#ffffff", fg="#555", font=self.label_font, anchor="w")
        self.invoice_label.pack(fill="x", pady=(4, 0))
        self.payment_label = tk.Label(accurate_frame, text="Payment CSV: None", bg="#ffffff", fg="#555", font=self.label_font, anchor="w")
        self.payment_label.pack(fill="x", pady=(4, 0))

        # Run Data Accurate Import button
        run_data_accurate_btn = tk.Button(accurate_frame, text="Run Data Accurate Import", command=self.run_data_accurate_import,
                                          font=self.btn_font, bg="#27ae60", fg="white", activebackground="#1e8449", relief="flat", padx=10, pady=8)
        run_data_accurate_btn.pack(pady=(15, 0), fill="x")

        # Frame for other CSV uploads
        other_frame = tk.LabelFrame(root, text="Other CSV Uploads", padx=15, pady=15, bg="#ffffff", fg="#444", font=self.label_font)
        other_frame.pack(padx=20, pady=10, fill="x")

        self.create_styled_button(other_frame, "Upload Xendit CSV", self.upload_xendit)
        self.create_styled_button(other_frame, "Upload Paper.ID CSV", self.upload_paperid)

        # Frame for other controls
        control_frame = tk.Frame(root, bg="#f5f7fa")
        control_frame.pack(padx=20, pady=15, fill="x")

        run_btn = tk.Button(control_frame, text="Run PaymentIntegrator", command=self.run_integeration,
                            font=self.btn_font, bg="#e67e22", fg="white", activebackground="#b35914", relief="flat", padx=10, pady=8)
        run_btn.pack(fill="x", pady=(0, 10))

        dashboard_btn = tk.Button(control_frame, text="Launch Streamlit Dashboard", command=self.launch_dashboard,
                                  font=self.btn_font, bg="#9b59b6", fg="white", activebackground="#6d3d7a", relief="flat", padx=10, pady=8)
        dashboard_btn.pack(fill="x")

    def center_window(self, width, height):
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def create_styled_button(self, parent, text, command):
        btn = tk.Button(parent, text=text, command=command,
                        font=self.btn_font, bg="#2980b9", fg="white", activebackground="#1c5d85", relief="flat", padx=10, pady=8)
        btn.pack(pady=5, fill="x")

    def open_accurate_upload_popup(self):
        popup = tk.Toplevel(self.root)
        popup.title("Upload Accurate CSV")
        popup.geometry("320x220")
        popup.configure(bg="#f0f4f8")
        popup.resizable(False, False)
        self.center_popup(popup, 320, 220)

        label = tk.Label(popup, text="Select CSV type to upload:", font=self.label_font, bg="#f0f4f8", fg="#333")
        label.pack(pady=12)

        btn_students = tk.Button(popup, text="Upload Students CSV", command=lambda: self.upload_students_csv(popup),
                                 font=self.btn_font, bg="#3498db", fg="white", activebackground="#217dbb", relief="flat", padx=10, pady=8)
        btn_students.pack(fill="x", padx=40, pady=5)

        btn_invoice = tk.Button(popup, text="Upload Invoice CSV", command=lambda: self.upload_invoice_csv(popup),
                                font=self.btn_font, bg="#3498db", fg="white", activebackground="#217dbb", relief="flat", padx=10, pady=8)
        btn_invoice.pack(fill="x", padx=40, pady=5)

        btn_payment = tk.Button(popup, text="Upload Payment CSV", command=lambda: self.upload_payment_csv(popup),
                                font=self.btn_font, bg="#3498db", fg="white", activebackground="#217dbb", relief="flat", padx=10, pady=5)
        btn_payment.pack(fill="x", padx=40)

    def center_popup(self, popup, width, height):
        popup.update_idletasks()
        x = (popup.winfo_screenwidth() // 2) - (width // 2)
        y = (popup.winfo_screenheight() // 2) - (height // 2)
        popup.geometry(f"{width}x{height}+{x}+{y}")

    def upload_students_csv(self, popup=None):
        path = filedialog.askopenfilename(title="Select Students CSV", filetypes=[("CSV files", "*.csv")])
        if path:
            self.students_csv = path
            self.students_label.config(text=f"Students CSV: {path.split('/')[-1]}")
            messagebox.showinfo("Selected", f"Students CSV selected:\n{path}")
        if popup:
            popup.destroy()

    def upload_invoice_csv(self, popup=None):
        path = filedialog.askopenfilename(title="Select Invoice CSV", filetypes=[("CSV files", "*.csv")])
        if path:
            self.invoice_csv = path
            self.invoice_label.config(text=f"Invoice CSV: {path.split('/')[-1]}")
            messagebox.showinfo("Selected", f"Invoice CSV selected:\n{path}")
        if popup:
            popup.destroy()

    def upload_payment_csv(self, popup=None):
        path = filedialog.askopenfilename(title="Select Payment CSV", filetypes=[("CSV files", "*.csv")])
        if path:
            self.payment_csv = path
            self.payment_label.config(text=f"Payment CSV: {path.split('/')[-1]}")
            messagebox.showinfo("Selected", f"Payment CSV selected:\n{path}")
        if popup:
            popup.destroy()

    def run_data_accurate_import(self):
        args = ['python', 'data_accurate.py']
        if self.students_csv:
            args.extend(['--students', self.students_csv])
        if self.invoice_csv:
            args.extend(['--invoice', self.invoice_csv])
        if self.payment_csv:
            args.extend(['--payment', self.payment_csv])

        if len(args) == 1:
            messagebox.showwarning("No files", "Please upload at least one Data Accurate CSV file before running.")
            return

        def target():
            try:
                subprocess.run(args, check=True)
                messagebox.showinfo("Success", "Data Accurate import completed successfully.")
            except subprocess.CalledProcessError:
                messagebox.showerror("Error", "Failed to run Data Accurate import.")

        threading.Thread(target=target, daemon=True).start()

    def upload_xendit(self):
        self.upload_file('xendit')

    def upload_paperid(self):
        self.upload_file('paperid')

    def upload_file(self, db_name):
        file_path = filedialog.askopenfilename(title=f"select CSV file for {db_name}", filetypes=[("CSV files", "*.csv")])

        if file_path:
            try:
                if db_name == 'accurate':
                    subprocess.run(['python', 'data_accurate.py', file_path], check=True)
                elif db_name == 'xendit':
                    subprocess.run(['python', 'payment_xendit.py', file_path], check=True)
                elif db_name == 'paperid':
                    subprocess.run(['python', 'payment_paperID.py', file_path], check=True)
                messagebox.showinfo("Success", "Payment integration completed")
            except subprocess.CalledProcessError:
                messagebox.showerror("Error", f"Failed to import CSV for {db_name}.")

    def run_integeration(self):
        try:
            subprocess.run(['python', 'app.py', 'run-integeration'], check=True)
            messagebox.showinfo("Success", "Payment integration completed")
        except subprocess.CalledProcessError:
            messagebox.showerror("Error", "Failed to run PaymentIntegrator")

    def launch_dashboard(self):
        try:
            subprocess.run(['streamlit', 'run', 'ar_dashboard2.py'])
            messagebox.showinfo("Info", "Streamlit Dashboard Launched.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to launch Streamlit Dashboard: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = FrontendApp(root)
    root.mainloop()