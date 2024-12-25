""" mft2csv.pyw v.0.3 - Create a list of files for a given NTFS drive, store the list as a csv file.

Lightweight and fast indexing of remote drives to know location of
backed-up or archived files on MS Windows local and external NTFS drives.
Produces lists fast because it is reading MFT (NTFS metadata) instead of actually
fetching files from a drive.

Code location and updates: https://github.com/epolkovnikov/TinyTools/mft2csv/
Developed by by Evgeny Polkovnikov, 2024
Thanks hansalemao for https://pypi.org/project/mft2df/

The tool can be used in GUI or in CLI mode.
CLI call example:
    python mft2csv.pyw E
    or
    pyrhon mft2csv.pyw E -o backup1.csv

GUI - *.pyw has to be associated with pythonw.exe
    Double click on the mft2csv.pyw
    Put the drive letter.
    If needed, adjust target/output dir and file (see the defaults below).

GUI in Administrator mode - needed mostly for internal NTFS drives.
    Right click on the bat file and select "Run as administrator"

Input:
    Drive letter - e.g. E
        Please note: For internal drives, the script must be executed as Administrator
        External drives did not required elevated privileges

Output: Tab-separated csv text UTF-8 with the following fields:
    * rmd5 - md5 hash of the file record (not the actual file!)
             calculated for the size, creation time and file name (without the full path)
             for ease of finding potential duplicates
    * FileSize - file size in bytes
    * FileNameCreated - file creation timestamp
    * FileNameLastModified - file modification timestamp. FreeFileSync may leave it unset
    * FullPath - path to the file on the drive, the drive letter and the following / or \ are omitted
    Default file location is the current work directory of the script.
    Default file name is calculated as <drive label>_<drive size>_<current time stamp>_<free space>.csv

Execution requirements:
Tested on MS Windows 11, Python 3.10.11. May also work on MS Windows 10
Exact Python requirements are listed in requirements.txt
"""
import traceback
import tkinter as tk
import tkinter.ttk as ttk
import tkinter.messagebox as tkMessageBox
import argparse
import datetime
import os
import shutil
import sys
import math
import re
from hashlib import md5
import ctypes
import ctypes.wintypes as wintypes
from mft2df import list_files_from_drive
from time import perf_counter
#import configparser
import ctypes
import ctypes.wintypes as wintypes

''' Generated with ChatGPT '''
def get_file_system_type(drive):
    """Detect the file system type of the given drive."""
    if drive.endswith(":"):
        drive += "\\"
    if not drive.endswith(":\\"):
        drive += ":\\"
    buffer = ctypes.create_unicode_buffer(1024)
    result = ctypes.windll.kernel32.GetVolumeInformationW(
        ctypes.c_wchar_p(drive),
        None,
        0,
        None,
        None,
        None,
        buffer,
        len(buffer)
    )
    if result:
        return buffer.value
    else:
        raise ctypes.WinError()

''' Generated with ChatGPT '''
def get_drive_label(drive):
    # The drive letter must be like C: or C:\ (C:\\ - '\' with escape)
    
    # Prepare buffers for the API call
    volume_name_buffer = ctypes.create_unicode_buffer(261)  # Max path length
    file_system_name_buffer = ctypes.create_unicode_buffer(261)
    serial_number = ctypes.c_uint32()
    max_component_length = ctypes.c_uint32()
    file_system_flags = ctypes.c_uint32()

    # Call GetVolumeInformationW
    result = ctypes.windll.kernel32.GetVolumeInformationW(
        ctypes.c_wchar_p(drive),
        volume_name_buffer,
        ctypes.sizeof(volume_name_buffer),
        ctypes.byref(serial_number),
        ctypes.byref(max_component_length),
        ctypes.byref(file_system_flags),
        file_system_name_buffer,
        ctypes.sizeof(file_system_name_buffer)
    )
    
    if result == 0:  # API call failed
        raise OSError(f"Failed to retrieve Label information for drive {drive}. Check if the drive {drive} exists.")

    # Extract the volume label from the buffer
    volume_label = volume_name_buffer.value
    if volume_label == '':
            volume_label = 'Unlabeled'
    return volume_label

''' Based on https://stackoverflow.com/a/827398 '''
def get_drive_letters():
    drives = []
    bitmask = ctypes.windll.kernel32.GetLogicalDrives()
    for letter in range(ord('A'), ord('Z') + 1):
        if bitmask & 1:
            drives.append(chr(letter))
        bitmask >>= 1

    return drives

def get_drives_and_labels():
    drive_letters = get_drive_letters()
    drives_and_labels = []
    for drive_letter in drive_letters:
        drive_type = get_file_system_type(drive_letter)
        drive_label = get_drive_label(drive_letter + ":\\")
        if drive_type == 'NTFS':
            drives_and_labels.append(f"{drive_letter}:, {drive_label}, {drive_type} - supported")
        else:
            drives_and_labels.append(f"{drive_letter}:, {drive_label}, {drive_type} - unsupported")
    if len(drives_and_labels) == 0:
        drives_and_labels=["?:, no drives? - unsupported"]

    return drives_and_labels

''' Based on https://stackoverflow.com/a/14822210 '''
def convert_size(size_bytes):
   if size_bytes == 0:
       return "0B"
   size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
   i = int(math.floor(math.log(size_bytes, 1024)))
   p = math.pow(1024, i)
   s = round(size_bytes / p)
   return f"{s}{size_name[i]}"

def calc_out_name(drive):
    try:
        label = get_drive_label(drive)
    except OSError as e:
        print(e)
        sys.exit(1)
    du = shutil.disk_usage(drive)
    total = convert_size(du.total)
    free = convert_size(du.free)
    time_stamp_str = datetime.datetime.today().strftime('%Y-%m-%dT%H%M')
    result = f"{label}_{total}_{time_stamp_str}_{free}.csv"
    return result

def rm_drive(full_path):
    _, path_without_drive = os.path.splitdrive(full_path)
    # os.path.splitroot is cleaner, but it requires Python 3.12
    return path_without_drive.lstrip('/\\')

def mft2csv(drive, target_file_name):
    drive_type = get_file_system_type(drive)
    if drive_type != 'NTFS':
        raise ValueError(f"Drive type {drive_type} is not NTFS - unsupported.")
    #TODO: Consider excluding: FileNameFlags = FILE_ATTRIBUTE_HIDDEN | FILE_ATTRIBUTE_SYSTEM
    work_columns = [
        'FileSize',
        'IsADirectory',
        'IsDeleted',
        #'StandardInfoLastModified',
        #'StandardInfoCreated',
        'FileNameLastModified',
        #'FileNameLastAccess',
        'FileNameCreated',
        #'StandardInfoFlags',
        'FileNameFlags',
        'FullPath',
    ]

    df=list_files_from_drive(drive=drive)
    
    if len(df) == 0:
        raise ValueError(f"No file records retrieved from drive {drive} MFT (empty dirs do not count as files).\nRetry as Administrator")

    for column_name_to_delete in df.columns.values.tolist():
        if column_name_to_delete not in work_columns:
            df = df.drop(column_name_to_delete, axis=1)

    index_non_files = df[ (df['IsADirectory'] == True) | (df['IsDeleted'] == True) ].index
    df.drop(index_non_files, inplace=True)

    df['FileName'] = df['FullPath'].apply(os.path.basename)
    just_path_column = df['FullPath'].apply(rm_drive)
    df['FullPath'] = just_path_column

    # Not using 'FileNameLastModified' in record md5, because it may be missing (the case after FreeFileSync)
    df['rmd5'] = df.apply(lambda x: md5(f"{x['FileSize']}{x['FileNameCreated']}{x['FileName']}".encode('utf-8')).hexdigest(), axis=1)

    df.to_csv(target_file_name,
              columns=('rmd5', 'FileSize', 'FileNameCreated', 'FileNameLastModified', 'FullPath'),
              sep='\t', na_rep='None', encoding='utf-8', index=False, header=True)

    return len(df)

class App(tk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.master.title("mft2csv")
        self.master.geometry('565x135')
        master.report_callback_exception = self.exception_handler

        self.src_lbl = ttk.Label(text="Drive to scan")
        self.src_lbl.grid(column=0, row=0)
        drives_and_labels = get_drives_and_labels()
        self.drive_value = tk.StringVar(self.master, drives_and_labels[0])
        self.drive_field = ttk.Combobox(self.master, textvariable=self.drive_value, width=62)
        self.drive_field['values'] = drives_and_labels
        self.drive_field['state'] = 'readonly'
        self.drive_field.grid(column=1, row=0, padx=2, pady=2)

        self.btn = tk.Button(text="Refresh Drives", command=self.refresh_btn_clicked)
        self.btn.grid(column=2, row=0, padx=2, pady=2)
        
        self.target_path_lbl = ttk.Label(text="Target Dir")
        self.target_path_lbl.grid(column=0, row=2)
        target_path = os.getcwd()
        self.target_path_field = ttk.Entry(width=80, textvariable=target_path)
        self.target_path_field.insert(0, target_path)
        self.target_path_field.grid(column=1, row=2, padx=2, pady=2, columnspan=2)

        self.target_file_lbl = ttk.Label(text="Target File")
        self.target_file_lbl.grid(column=0, row=3)
        self.target_file_name=tk.StringVar(self.master)
        self.target_file_field = ttk.Entry(width=80, textvariable=self.target_file_name)
        self.update_target_file()
        self.target_file_field.grid(column=1, row=3, padx=2, pady=2, columnspan=2)

        self.drive_value.trace("w", self.update_target_file)

        self.btn = tk.Button(text="Go!", command=self.go_btn_clicked)
        self.btn.grid(column=0, row=4, padx=2, pady=3, columnspan=3)

        self.status_lbl = ttk.Label(text="Click [Go!]")
        self.status_lbl.grid(column=0, row=5, columnspan=3, padx=2, pady=2)

    def update_target_file(self, *args):
        selected_drive = self.drive_value.get()
        if selected_drive:
            m = re.match('^([A-Z])', selected_drive)
            if m:
                drive = m.group(1)
                self.target_file_name.set(calc_out_name(drive + ":\\"))

    def refresh_btn_clicked(self):
        drives_and_labels = get_drives_and_labels()
        self.drive_value.set(drives_and_labels[0])
        self.drive_field['values'] = drives_and_labels
        self.drive_field.current()

    def go_btn_clicked(self):
        self.btn.config(state=tk.DISABLED)
        selected_drive = self.drive_value.get()
        m = re.match('^([A-Z])', selected_drive)
        drive = "?"
        if m:
            drive = m.group(1)
            self.target_file_name.set(calc_out_name(drive + ":\\"))

        target_file_name = self.target_file_field.get()
        if target_file_name == "[Auto from drive label, letter and the execution time]":
           target_file_name = calc_out_name(drive)
        
        target_full_path = os.path.join(self.target_path_field.get(), target_file_name)

        status = f'Parsing drive {drive} MFT to {target_full_path}'
        self.status_lbl.configure(text=status)
        self.status_lbl.update()
        # All exceptions are handled by the ttk exception_handler
        rec_count = mft2csv(drive, target_full_path) 
        self.btn.config(state=tk.NORMAL)
        self.status_lbl.configure(text=f'Done with {drive} to {target_full_path}')
        status = f'Wrote drive {drive} {rec_count} file records to {target_full_path}'
        tkMessageBox.showinfo('Status', str(status))

    def exception_handler(self, exc, val, tb):
        self.btn.config(state=tk.NORMAL)
        self.status_lbl.configure(text="Got error. Please correct and re-try")
        tkMessageBox.showerror('Error', str(val))
    
def main():

    if re.search('pythonw.exe', sys.executable):
        root = tk.Tk()
        app = App(root)
        app.mainloop()
    else:
        # Create an ArgumentParser object
        parser = argparse.ArgumentParser(
            prog="mft2csv",
            description="Create a csv list of files for a given NTFS drive.\nReads MFT instead of fetching actual files to produce the list fast.",
            epilog="See for details"
            )
        
        # Positional argument for the drive letter
        parser.add_argument(
            "drive",
            type=str,
            help="Drive letter on MS Windows (e.g., C, D, E).",
        )
        
        parser.add_argument(
            "-o", "--output",
            type=str,
            help="Optional output file name (default: filelist.csv).",
        )
        
        args = parser.parse_args()
        drive = args.drive.upper()  # Convert to uppercase for standardization

        if drive.endswith(":"):
            drive += "\\"
        if not drive.endswith(":\\"):
            drive += ":\\"

        if args.output == None:
            target_file_name = calc_out_name(drive)
            target_full_path = os.path.join(os.getcwd(), target_file_name)
        else:
            target_full_path = args.output

        print(f'Parsing drive {drive} MFT to {target_full_path}')

        try:
            rec_count = mft2csv(drive, target_full_path)
        except ValueError as e:
            print(e)
            sys.exit(1)

        print(f'Wrote {rec_count} file records of drive {drive} to {target_full_path}')

if __name__ == "__main__":
    main()
