#!/usr/bin/env python3

import os
import re
import time 
import glob
import argparse
import stat 
from datetime import datetime

# Attempt to import Pillow (PIL)
PIL_AVAILABLE = False
try:
    from PIL import Image, UnidentifiedImageError
    PIL_AVAILABLE = True
except ImportError:
    pass

# --- Configuration ---
EXTENSIONS = re.compile(
    r'\.(3g2|3gp|asf|avi|bmp|divx|flv|gif|jfif|jpg|jpeg|m1v|mov|mp4|mpeg|mpe|mpg|png|ram|rm|ts|viv|webm|webp|wmv)$', # Added webp
    re.IGNORECASE
)
EXIF_DATE_FALLBACK_TAGS = {
    'DateTimeOriginal': 0x9003,
    'DateTimeDigitized': 0x9004,
}
DATE_STAMP_FORMAT_REGEX_STR = r"\d{4}\.\d{2}\.\d{2}\.\d{2}\.\d{2}\.\d{2}"
STANDALONE_DATE_STAMP_REGEX = re.compile(f"^{DATE_STAMP_FORMAT_REGEX_STR}")
DATE_STAMP_LENGTH = 19
# --- End Configuration ---


def _try_parse_xmp_create_date(img, filepath, vprint_func):
    xmp_date_str_iso = None
    try:
        xmp_info = img.getxmp()
        if xmp_info and 'xmp' in xmp_info:
            xmp_packet = xmp_info['xmp']
            xmp_data_string = ""
            if isinstance(xmp_packet, bytes):
                xmp_data_string = xmp_packet.decode('utf-8', errors='ignore')
            elif isinstance(xmp_packet, str):
                xmp_data_string = xmp_packet
            
            if xmp_data_string:
                match = re.search(r"<xmp:CreateDate>([^<]+)</xmp:CreateDate>", xmp_data_string)
                if match:
                    xmp_date_str_iso = match.group(1).strip()
                    vprint_func(f"  - Found XMP xmp:CreateDate: {xmp_date_str_iso}")
                else:
                    match = re.search(r"<photoshop:DateCreated>([^<]+)</photoshop:DateCreated>", xmp_data_string)
                    if match:
                        xmp_date_str_iso = match.group(1).strip()
                        vprint_func(f"  - Found XMP photoshop:DateCreated: {xmp_date_str_iso}")
        
        if xmp_date_str_iso:
            try:
                dt_object = None
                if xmp_date_str_iso.endswith('Z'):
                    dt_object = datetime.fromisoformat(xmp_date_str_iso[:-1] + '+00:00')
                else:
                    dt_object = datetime.fromisoformat(xmp_date_str_iso)
                
                parsed_date = dt_object.strftime('%Y.%m.%d.%H.%M.%S')
                vprint_func(f"  - Parsed XMP date: {parsed_date}")
                return parsed_date
            except ValueError:
                vprint_func(f"  Warning: Could not parse ISO XMP date string '{xmp_date_str_iso}' with fromisoformat.")
                try:
                    dt_part = xmp_date_str_iso[:19].replace('T', ' ')
                    dt_object = datetime.strptime(dt_part, '%Y-%m-%d %H:%M:%S')
                    parsed_date = dt_object.strftime('%Y.%m.%d.%H.%M.%S')
                    vprint_func(f"  - Parsed XMP date (fallback method): {parsed_date}")
                    return parsed_date
                except ValueError:
                    vprint_func(f"  Warning: Fallback parsing of XMP date part '{dt_part}' also failed.")
                    pass 
    except AttributeError:
        vprint_func(f"  - XMP check: img.getxmp() not available (Pillow < 7.2.0 or not an image type supporting it).")
    except Exception as e_xmp:
        vprint_func(f"  Warning: Error processing XMP data from {os.path.basename(filepath)}: {e_xmp}")
    return None


def _try_parse_exif_tags(img, filepath, vprint_func):
    exif_data = img._getexif()
    if exif_data:
        exif_date_str_from_tags = None
        for tag_name, tag_id in EXIF_DATE_FALLBACK_TAGS.items():
            date_val = exif_data.get(tag_id)
            if date_val:
                vprint_func(f"  - Found EXIF tag '{tag_name}' (ID: {tag_id}): {date_val}")
                exif_date_str_from_tags = str(date_val)
                break 
        
        if exif_date_str_from_tags:
            try:
                cleaned_date_str = exif_date_str_from_tags.strip().replace('\x00', '')
                dt_object = datetime.strptime(cleaned_date_str, '%Y:%m:%d %H:%M:%S')
                parsed_date = dt_object.strftime('%Y.%m.%d.%H.%M.%S')
                vprint_func(f"  - Parsed EXIF date: {parsed_date}")
                return parsed_date
            except ValueError:
                vprint_func(f"  Warning: Could not parse EXIF date string '{exif_date_str_from_tags}' from tag.")
                pass 
    return None


def get_exif_date(filepath, vprint_func):
    if not PIL_AVAILABLE:
        vprint_func(f"  - Pillow library not available, cannot read EXIF/XMP for {os.path.basename(filepath)}")
        return None

    try:
        with Image.open(filepath) as img:
            vprint_func(f"  - Checking XMP metadata for CreateDate for {os.path.basename(filepath)}...")
            xmp_parsed_date = _try_parse_xmp_create_date(img, filepath, vprint_func)
            if xmp_parsed_date:
                return xmp_parsed_date

            vprint_func(f"  - XMP CreateDate not found/parsed, trying standard EXIF tags for {os.path.basename(filepath)}...")
            exif_tag_parsed_date = _try_parse_exif_tags(img, filepath, vprint_func)
            if exif_tag_parsed_date:
                return exif_tag_parsed_date
            
            vprint_func(f"  - No usable date found from preferred XMP or standard EXIF tags for {os.path.basename(filepath)}.")
            return None 

    except FileNotFoundError:
        vprint_func(f"  Error: File not found during EXIF/XMP processing: {filepath}")
    except UnidentifiedImageError:
        vprint_func(f"  Warning: Pillow could not identify image file (or not an image): {os.path.basename(filepath)}")
    except Exception as e_open:
        vprint_func(f"  Warning: Could not open/process image {os.path.basename(filepath)} for EXIF/XMP: {e_open}")
    return None


def try_remove_executable_bits(filepath, verbose_flag):
    def vprint_chmod(*pargs, **kwargs):
        if verbose_flag:
            print(*pargs, **kwargs)
            
    try:
        current_mode = os.stat(filepath).st_mode
        if not stat.S_ISREG(current_mode):
            return False

        new_mode = current_mode & ~stat.S_IXUSR & ~stat.S_IXGRP & ~stat.S_IXOTH
        if new_mode != current_mode:
            os.chmod(filepath, new_mode)
            vprint_chmod(f"  - Permissions adjusted for: {os.path.basename(filepath)}")
            return True
        else:
            vprint_chmod(f"  - Permissions already correct for: {os.path.basename(filepath)}")
            return False
    except FileNotFoundError:
        return False
    except Exception as e_chmod:
        print(f"Warning: Could not change permissions for {filepath}: {e_chmod}")
        return False

def main():
    parser = argparse.ArgumentParser(
        description="Rename media files using EXIF or file creation date, and remove executable bits.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "-t", "--time_from_exif",
        action="store_true",
        help="Use EXIF date for filename if available.\n"
             "If EXIF/XMP date is not found/readable, fallback to file creation time (ctime)."
    )
    parser.add_argument(
        "-f", "--force",
        action="store_true",
        help="Force reprocessing of files. \n"
             " - If file starts with the *correct* date, -f re-processes/re-cleans the suffix.\n"
             " - If file has correct date *elsewhere* in name, -f processes it.\n"
             " (Files starting with an *incorrect* date are now re-processed by default)."
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output, showing detailed processing information and previews."
    )
    args = parser.parse_args()

    _verbose_mode = args.verbose
    def vprint(*pargs, **kwargs):
        if _verbose_mode:
            print(*pargs, **kwargs)

    if args.time_from_exif and not PIL_AVAILABLE:
        print("Warning: Pillow library is not installed, but -t flag was used. " 
              "EXIF/XMP data cannot be read. Script will use file creation time (ctime) instead.\n"
              "To enable EXIF/XMP processing, install Pillow: pip install Pillow")

    seen = {}
    eligible_files_not_renamed_paths = set()
    successfully_renamed_original_paths = set()

    scanned_files_count = 0
    eligible_files_count = 0
    skipped_datestamped_no_force_count = 0 
    skipped_empty_after_strip_count = 0
    skipped_contains_date_no_force_count = 0
    skipped_no_change_count = 0
    renamed_count = 0
    total_permissions_adjusted = 0

    vprint("Scanning files...")
    for original_filepath in glob.glob("*"):
        scanned_files_count += 1
        if not os.path.isfile(original_filepath):
            continue

        if not EXTENSIONS.search(original_filepath):
            continue
        
        eligible_files_count += 1
        original_basename = os.path.basename(original_filepath)
        vprint(f"\nProcessing: {original_basename}")

        file_date_str = None 
        date_source = ""

        if args.time_from_exif:
            exif_date = get_exif_date(original_filepath, vprint) 
            if exif_date:
                file_date_str = exif_date
                date_source = "EXIF/XMP"
            else:
                vprint(f"  - EXIF/XMP date not found for {original_basename}, falling back to ctime.")
                try:
                    ctime = os.lstat(original_filepath).st_ctime
                    file_date_str = time.strftime("%Y.%m.%d.%H.%M.%S", time.localtime(ctime))
                    date_source = "ctime (EXIF/XMP fallback)"
                    vprint(f"  - Using ctime: {file_date_str}")
                except Exception as e:
                    print(f"Error getting ctime for {original_filepath}: {e}") 
                    eligible_files_not_renamed_paths.add(original_filepath)
                    continue
        else: 
            try:
                ctime = os.lstat(original_filepath).st_ctime
                file_date_str = time.strftime("%Y.%m.%d.%H.%M.%S", time.localtime(ctime))
                date_source = "ctime (default)"
                vprint(f"  - Using ctime: {file_date_str}")
            except Exception as e:
                print(f"Error getting ctime for {original_filepath}: {e}") 
                eligible_files_not_renamed_paths.add(original_filepath)
                continue

        if not file_date_str: 
            print(f"Warning: Could not determine date for {original_filepath}. Skipping.") 
            eligible_files_not_renamed_paths.add(original_filepath)
            continue

        filename_to_process = original_basename
        is_already_datestamped_at_start_match = STANDALONE_DATE_STAMP_REGEX.match(original_basename)

        if is_already_datestamped_at_start_match:
            filename_current_date_prefix = original_basename[:DATE_STAMP_LENGTH]
            vprint(f"  - File starts with a date stamp pattern: '{filename_current_date_prefix}'")

            if filename_current_date_prefix == file_date_str:
                if not args.force:
                    vprint(f"  - Skipping (starts with correct date '{file_date_str}' and no -f to re-process suffix).")
                    skipped_datestamped_no_force_count += 1 
                    eligible_files_not_renamed_paths.add(original_filepath)
                    continue
                else:
                    vprint(f"  - Force mode: File starts with correct date '{file_date_str}'. Will strip and re-process suffix.")
                    temp_name = original_basename[DATE_STAMP_LENGTH:]
                    if temp_name.startswith("_"):
                        temp_name = temp_name[1:]
                    filename_to_process = temp_name
                    
                    temp_base, temp_ext = os.path.splitext(filename_to_process)
                    if not temp_base and filename_to_process.startswith('.'):
                         filename_to_process = f"recovered{filename_to_process}"
                         vprint(f"  - Name became extension-only after stripping correct date, set to '{filename_to_process}'")
                    elif not filename_to_process or not temp_base:
                        print(f"Warning: Filename '{original_basename}' became invalid ('{filename_to_process}') after stripping correct date with -f. Skipping.")
                        skipped_empty_after_strip_count += 1
                        eligible_files_not_renamed_paths.add(original_filepath)
                        continue
            else:
                vprint(f"  - File starts with date '{filename_current_date_prefix}', but new date is '{file_date_str}'. Will re-process.")
                vprint(f"  - Stripping leading incorrect date stamp(s)...")
                temp_name = original_basename
                stripped_count = 0
                for i_strip in range(2): 
                    match_obj_strip = STANDALONE_DATE_STAMP_REGEX.match(temp_name)
                    if match_obj_strip:
                        old_temp_name_in_strip = temp_name
                        temp_name = temp_name[DATE_STAMP_LENGTH:]
                        if temp_name.startswith("_"):
                            temp_name = temp_name[1:]
                        stripped_count += 1
                        vprint(f"    - Strip {i_strip+1}: '{old_temp_name_in_strip[:DATE_STAMP_LENGTH + (1 if old_temp_name_in_strip[DATE_STAMP_LENGTH:].startswith('_') else 0)]}' -> remaining: '{temp_name}'")
                    else:
                        break
                if stripped_count > 0:
                    filename_to_process = temp_name
                    vprint(f"  - Base name after stripping incorrect date(s): '{filename_to_process}'")
                    temp_base, temp_ext = os.path.splitext(filename_to_process)
                    if not temp_base and filename_to_process.startswith('.'):
                         filename_to_process = f"recovered{filename_to_process}"
                         vprint(f"  - Name became extension-only, set to '{filename_to_process}'")
                    elif not filename_to_process or not temp_base:
                        print(f"Warning: Filename '{original_basename}' became invalid ('{filename_to_process}') after stripping incorrect date(s). Skipping.")
                        skipped_empty_after_strip_count += 1
                        eligible_files_not_renamed_paths.add(original_filepath)
                        continue
        elif file_date_str in original_basename and not args.force: 
            vprint(f"  - Skipping (already contains target date '{file_date_str}' elsewhere, no -f).")
            skipped_contains_date_no_force_count += 1
            eligible_files_not_renamed_paths.add(original_filepath)
            continue
        
        name_part, ext_part = os.path.splitext(filename_to_process)
        processed_name_part = name_part.lower()
        processed_ext_part = ext_part.lower()

        if processed_ext_part == ".jpeg":
            processed_ext_part = ".jpg"

        processed_name_part = re.sub(r'[\[\]\(\)]', '', processed_name_part)
        processed_name_part = re.sub(r'[\s,+&]', '', processed_name_part)
        processed_name_part = re.sub(r'^_+', '', processed_name_part)
        
        processed_name_part = re.sub(r'^\.+', '', processed_name_part)

        if not processed_name_part:
            processed_name_part = "untitled" if processed_ext_part else "untitled_file"
        
        final_name_suffix = f"_{processed_name_part}{processed_ext_part}"
        final_name = f"{file_date_str}{final_name_suffix}"
        vprint(f"  - Proposed new name components: Date='{file_date_str}', Suffix='{final_name_suffix}' -> Tentative: '{final_name}'")

        if final_name == original_basename:
            vprint(f"  - Skipping (no change needed).")
            skipped_no_change_count += 1
            eligible_files_not_renamed_paths.add(original_filepath)
            continue

        counter = 1
        temp_final_name = final_name
        base_final_name_for_counter, final_ext_for_counter = os.path.splitext(final_name)
        
        while temp_final_name in seen or os.path.exists(temp_final_name):
            if temp_final_name == original_basename: break 
            vprint(f"  - Target '{temp_final_name}' exists or conflicts, trying next...")
            temp_final_name = f"{base_final_name_for_counter}_{counter}{final_ext_for_counter}"
            counter += 1
            if counter > 100:
                vprint(f"  Warning: Could not find unique name for '{original_basename}' -> '{final_name}' after 100 attempts. Skipping.")
                temp_final_name = None
                break
        
        if temp_final_name is None or temp_final_name == original_basename:
            if temp_final_name == original_basename:
                vprint(f"  - Skipping (resolved to no change after conflict check).")
                skipped_no_change_count +=1
            eligible_files_not_renamed_paths.add(original_filepath)
            continue

        final_name = temp_final_name
        vprint(f"  - Final target name: '{final_name}' (Date from: {date_source})")
        seen[final_name] = (original_filepath, date_source)
    
    vprint("\n--- Scan Summary ---") 
    if args.verbose: 
        if skipped_datestamped_no_force_count > 0:
            vprint(f"  Skipped (starts with correct date, no -f): {skipped_datestamped_no_force_count}")
        if skipped_empty_after_strip_count > 0:
            vprint(f"  Skipped (empty/invalid after stripping): {skipped_empty_after_strip_count}")
        if skipped_contains_date_no_force_count > 0:
            vprint(f"  Skipped (contained target date elsewhere, no -f): {skipped_contains_date_no_force_count}")
        if skipped_no_change_count > 0: 
             vprint(f"  Skipped (no change ultimately needed): {skipped_no_change_count}")
    
    if not seen:
        vprint("No files to rename based on scan criteria.")
    else:
        if args.verbose:
            vprint(f"\nPreview of renames ({len(seen)} files):")
            for new_name_key, (old_name_val, src) in sorted(seen.items()):
                vprint(f"  '{os.path.basename(old_name_val)}' -> '{new_name_key}' (using {src} date)")
        
        vprint("\nRenaming files...")
        for new_name, (old_name, _) in sorted(seen.items()):
            try:
                os.rename(old_name, new_name)
                renamed_count +=1
                successfully_renamed_original_paths.add(old_name)
                vprint(f"  Renamed: '{os.path.basename(old_name)}' -> '{new_name}'")
                if try_remove_executable_bits(new_name, args.verbose):
                    total_permissions_adjusted +=1
            except Exception as e:
                print(f"Error renaming {old_name} to {new_name}: {e}") 
                eligible_files_not_renamed_paths.add(old_name) 

    final_paths_to_chmod_original = eligible_files_not_renamed_paths - successfully_renamed_original_paths
    if final_paths_to_chmod_original:
        vprint(f"\nAdjusting permissions for {len(final_paths_to_chmod_original)} eligible file(s) that were not renamed (or failed rename)...")
        for path_to_chmod in final_paths_to_chmod_original:
            if os.path.exists(path_to_chmod):
                if try_remove_executable_bits(path_to_chmod, args.verbose):
                    total_permissions_adjusted += 1
        vprint("Permission adjustment for non-renamed files complete.")

    print("\n--- Summary ---")
    print(f"Total files scanned: {scanned_files_count}")
    print(f"Eligible media files: {eligible_files_count}")
    
    if renamed_count > 0:
        print(f"Files renamed: {renamed_count}")
    elif eligible_files_count > 0 :
        print("No files were renamed (e.g., already correct, skipped, or no changes identified).")
    else: 
        print("No eligible media files found to process or rename.")
        
    if total_permissions_adjusted > 0:
        print(f"File permissions adjusted: {total_permissions_adjusted}")
    elif eligible_files_count > 0:
        vprint("No file permissions required changes (or adjustments failed where noted).")

if __name__ == "__main__":
    main()
