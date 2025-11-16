import re
import os
import logging
from numpy import nan
import pandas as pd


class LuNum:
    """Represents a Lock Up Number with its associated text block."""

    def __init__(self, match_item, block_text=""):
        self._match = match_item
        self._block_text = block_text
        self._fixed_number = None
        self._is_duplicate = None
        self._is_missing = False

    @property
    def number(self):
        """The lock up number as an integer (corrected if fixed)."""
        if self._fixed_number is not None:
            return self._fixed_number
        return int(self._match.group("number"))

    @property
    def original_number(self):
        """The original lock up number before any fixes."""
        return int(self._match.group("number"))

    @property
    def is_fixed(self):
        """True if this LuNum was corrected."""
        return self._fixed_number is not None

    @property
    def is_duplicate(self):
        """True if this LuNum is a duplicate."""
        return self._is_duplicate
    
    @property
    def is_missing(self):
        """True if this LuNum is a placeholder for a missing number."""
        return self._is_missing

    @property
    def start(self):
        """Start position of the number in the original text."""
        return self._match.start("number")

    @property
    def end(self):
        """End position of the number in the original text."""
        return self._match.end("number")

    @property
    def block_start(self):
        """Start position of the entire match (including whitespace)."""
        return self._match.start()

    @property
    def block_end(self):
        """End position of the block (start of next LU or end of text)."""
        return self.block_start + len(self._block_text)

    @property
    def block(self):
        """The text block associated with this lock up number."""
        return self._block_text

    @property
    def span(self):
        """Tuple of (block_start, block_end)."""
        return (self.block_start, self.block_end)

    def __repr__(self):
        flags = []
        if self.is_fixed:
            flags.append("fixed")
        if self.is_duplicate:
            flags.append("duplicate")
        if self.is_missing:
            flags.append("MISSING")
        flag_str = f" ({', '.join(flags)})" if flags else ""
        return f"<LuNum number={self.number}{flag_str}, span={self.span}>"


def create_lunums(lu_text="", lu_regex=r"^\s+(?P<number>\d{2,3})(?= )", quite = True):
    """
    Create LuNum objects from text containing lock up numbers.

    Args:
        lu_text: Text containing lock up numbers
        lu_regex: Regex pattern to match lock up numbers

    Returns:
        List of LuNum objects with associated text blocks

    Raises:
        ValueError: If no lock up numbers are found
    """
    lunums_iter = re.finditer(lu_regex, lu_text, flags=re.M)
    lunums_list = list(lunums_iter)

    if not lunums_list:
        raise ValueError("No Lock Up Numbers Found! Check the Lock up list.")

    lu_nums = []

    for i, match in enumerate(lunums_list):
        # Determine the end of this block (start of next match or end of text)
        block_start = match.start()

        if i < len(lunums_list) - 1:
            # Not the last item - block ends at start of next match
            block_end = lunums_list[i + 1].start()
        else:
            # Last item - block goes to end of text
            block_end = len(lu_text)

        # Extract the block text
        block_text = lu_text[block_start:block_end]

        # Create LuNum object
        current_lu = LuNum(match, block_text)
        lu_nums.append(current_lu)

        # Debug output
        if not quite: 
            print(f"LU #{current_lu.number}: span={current_lu.span}, block_length={len(current_lu.block)}")

    return lu_nums


def validate_normalize_lunums(lunums, start_num=1):
    """
    Validates LuNum sequence and fixes out-of-order numbers.
    Flags duplicates after corrections are made.

    Args:
        lunums: List of LuNum objects
        start_num: Expected starting number (default: 1)

    Returns:
        fixed_lunums: List of LuNum objects (fixed if needed)
    """
    if not lunums:
        raise ValueError("No LuNum objects to validate")

    # Extract numbers for validation
    numbers = [lu.number for lu in lunums]
    start_num = numbers[0]

    # Validate sequence (check for out-of-order only)
    expected_num = start_num
    out_of_order = []

    for i, num in enumerate(numbers):
        if num is None:
            continue

        # Check for sequential order
        if num != expected_num:
            print(
                f"❌ Out of order: Expected {expected_num}, found {num} at position {i}")
            out_of_order.append((i, expected_num, num))

        expected_num = num + 1

    # Fix the sequence first
    if out_of_order:
        print(f"\n🔧 Fixing sequence... ({len(out_of_order)} out of order)")
        fixed_lunums = []
        fixes_applied = 0

        for i, lu in enumerate(lunums):
            original_num = numbers[i]

            # Determine if this number needs fixing
            needs_fixing = False
            correct_num = None

            # Check if current number breaks the sequence
            if i > 0 and i < len(numbers) - 1:
                # Middle element: check if it's between prev and next
                prev_num = numbers[i - 1]
                next_num = numbers[i + 1]

                # If prev and next are sequential but current is not, fix it
                if prev_num is not None and next_num is not None:
                    if next_num == prev_num + 2 and original_num != prev_num + 1:
                        needs_fixing = True
                        correct_num = prev_num + 1

            elif i == 0 and len(numbers) > 1:
                # First element: check if it matches expected start or breaks sequence with next
                next_num = numbers[i + 1]
                if next_num is not None:
                    if original_num != start_num or next_num != original_num + 1:
                        # Check if next is sequential from start
                        if next_num == start_num + 1:
                            needs_fixing = True
                            correct_num = start_num

            elif i == len(numbers) - 1 and len(numbers) > 1:
                # Last element: check sequence with previous
                prev_num = numbers[i - 1]
                if prev_num is not None and original_num != prev_num + 1:
                    needs_fixing = True
                    correct_num = prev_num + 1

            # Apply fix if needed
            if needs_fixing and correct_num is not None:
                # Fix the number in the block text
                old_num_str = str(original_num)
                new_num_str = str(correct_num).zfill(
                    len(old_num_str))  # Preserve padding

                # Replace in block text
                fixed_block = lu.block.replace(
                    f"{old_num_str} ",
                    f"{new_num_str} ",
                    1  # Only replace first occurrence
                )

                # Create new LuNum with fixed data
                fixed_lu = LuNum.__new__(LuNum)
                fixed_lu._match = lu._match
                fixed_lu._block_text = fixed_block
                fixed_lu._fixed_number = correct_num
                fixed_lu._is_duplicate = False
                fixed_lu._is_missing = False

                print(f"  Position {i}: LU #{original_num} → #{correct_num}")
                fixes_applied += 1

                fixed_lunums.append(fixed_lu)
            else:
                # Keep original
                lu._is_duplicate = False
                fixed_lunums.append(lu)

        print(f"Sequence correction complete: {fixes_applied} fixes applied")
    else:
        # No fixes needed, use original lunums
        fixed_lunums = lunums
        for lu in fixed_lunums:
            lu._is_duplicate = False

    # Now check for duplicates in the corrected sequence
    corrected_numbers = [lu.number for lu in fixed_lunums]
    seen_numbers = set()
    duplicates = []

    for i, num in enumerate(corrected_numbers):
        if num in seen_numbers:
            duplicates.append(i)
            fixed_lunums[i]._is_duplicate = True
            print(f"❌ Duplicate found after correction: {num} at position {i}")
        seen_numbers.add(num)

    if duplicates:
        print(
            f"\n⚠️  {len(duplicates)} duplicate(s) flagged after sequence correction")
    elif not out_of_order:
        print("✓ Sequence is valid!")

    # Find missing numbers in the sequence
    if fixed_lunums:
        min_num = min(corrected_numbers)
        max_num = max(corrected_numbers)
        expected_set = set(range(min_num, max_num + 1))
        found_set = set(corrected_numbers)
        missing_numbers = sorted(expected_set - found_set)
        
        if missing_numbers:
            print(f"\n🔍 Found {len(missing_numbers)} missing lock up number(s): {missing_numbers}")
            print("Creating placeholder LuNum objects for missing numbers...")
            
            # Create placeholder LuNum objects for missing numbers
            for missing_num in missing_numbers:
                # Create a placeholder LuNum
                placeholder_lu = LuNum.__new__(LuNum)
                placeholder_lu._match = None  # No actual match
                placeholder_lu._block_text = ""  # Empty block
                placeholder_lu._fixed_number = missing_num
                placeholder_lu._is_duplicate = False
                placeholder_lu._is_missing = True  # Flag as missing
                
                # Insert in correct position to maintain order
                insert_pos = 0
                for i, lu in enumerate(fixed_lunums):
                    if lu.number < missing_num:
                        insert_pos = i + 1
                    else:
                        break
                
                fixed_lunums.insert(insert_pos, placeholder_lu)
                print(f"  Created placeholder for LU #{missing_num} at position {insert_pos}")
            
            print(f"Added {len(missing_numbers)} placeholder(s) to sequence")

    return fixed_lunums


def select_line(text: str, line_number: int):
    '''
    Helper function to select line in a re search function. 
    '''
    if line_number == 1:
        start_index = 0
        end_index = re.search(".*$", text, flags=re.M).end()
    else:
        regex_start = ".*\\n" * (line_number - 1)
        regex_end = regex_start + ".*$"

        start_index = re.search(regex_start, text, flags=re.M).end()
        end_index = re.search(regex_end, text, flags=re.M).end()

    return text[start_index:end_index]


def handle_nulls(scrape_var, strip=False):
    '''
    Handles cases where regex search funds nothing and returns nan.
    '''
    if scrape_var is not None:
        if not strip:
            handled_var = scrape_var.group()
        else:
            handled_var = scrape_var.group().strip()
    else:
        handled_var = nan

    return handled_var


def broaden_search(regex: str, block, line: int):
    '''
    Creates a fall back to search the entire block. 

    Regex should be unlikely to occur elsewhere in the LU block. 
    '''
    attribute = re.search(regex, select_line(block, line), flags=re.M)
    if attribute is not None:
        attribute = attribute.group().strip()
    else:
        attribute = handle_nulls(re.search(regex, block))

    return attribute


class LockUpBlock():
    def __init__(self, lu_number, block, errored_lu=False):
        self.lu_number = lu_number
        self.block = block

        # when errored_lu is true you can cal details individually
        if not errored_lu:
            self.get_lo_details()
            self.get_case_details()
            self.get_arrest_details()
        else:
            self.get_lo_details()

    def get_lo_details(self):
        # Age, Gender, and Race all fall back to search the entire block, since they are the most used values in analysis and have standard searches.
        self.age = re.search("\d\d(?= year old)", select_line(self.block, 1))
        if self.age is not None:
            self.age = self.age.group().strip()
        else:
            self.age = handle_nulls(re.search("\d\d(?= year old)", self.block))

        self.gender = re.search("Male|Female(?= )", select_line(self.block, 2))
        if self.gender is not None:
            self.gender = self.gender.group().strip()
        else:
            self.gender = handle_nulls(
                re.search("Male|Female(?= )", self.block))

        self.race = re.search(
            "(?<=     )White|Black [ao]r African-American|Hispanic or Latino(?=[ -])", select_line(self.block, 2))
        if self.race is not None:
            self.race = self.race.group().strip()
        else:
            self.race = handle_nulls(re.search(
                "(?<=     )White|B[il]ack [ao]r African-American|Hispanic or Latino(?=[ -])", self.block))

        # names search based on a name regex pattern; regex patterns tries to match first without middle name then with middle name
        # allows for up to 6 spaces between the first and middle name
        # falls back searching for everything on between the adjecent columns
        self.true_name = re.search(
            r"((?<=     )[A-Za-z.’'\- !]+, [A-Za-z.’'\-!]+(?=          ))|([A-Za-z.’'\- !]+, [A-Za-z.'\-!]+[ ]{,6}[A-Za-z.'\-!]+(?=     ))", select_line(self.block, 1))
        if self.true_name is not None:
            self.true_name = self.true_name.group().strip()
        else:
            self.true_name = handle_nulls(re.search(
                r"(?<=\d{2}\/\d{2}\/\d{4} \d{4})[0-9A-Za-z.’'\- ,!]+(?=\d\d[ ]year[ ]old)|(?<=\d{2}\/\d{2}\/\d{4}\d{4})[0-9A-Za-z.’'\- ,!]+(?=\d\d[ ]year[ ]old)", select_line(self.block, 1)))

        self.name = re.search(
            r"((?<=     )[A-Za-z.’'\- !]+, [A-Za-z.’'\-!]+(?=     ))|([A-Za-z.’'\- !]+, [A-Za-z.’'\-!]+[ ]{,6}[A-Za-z.'\-!]+(?=          ))", select_line(self.block, 2))

        if self.name is not None:
            self.name = self.name.group().strip()
        else:
            self.name = handle_nulls(re.search(
                r"(?<=\d{9})[A-Za-z.'\- ,]+(?=White|Black [ao]r African-American|Hispanic [ao]r Latino)", select_line(self.block, 2)), strip=True)

    def get_arrest_details(self):

        self.arrest_number = handle_nulls(
            re.search("(?<=     )\d{9}(?=     )", select_line(self.block, 2)))

        arresting_officer = re.search(
            r"(?P<name>[A-Za-z.'\- ]+, [A-Za-z.'\-]+|(?<=[0-9])[A-Za-z.'\- ]+)(?P<badge>[ 0-9]*)", select_line(self.block, 3), flags=re.M)

        if arresting_officer is not None:
            if arresting_officer.group("name") is not None:
                self.arresting_officer_name = arresting_officer.group(
                    "name").strip()
            else:
                self.arresting_officer_name = nan

            if arresting_officer.group("badge") is not None:
                self.arresting_officer_badge = arresting_officer.group(
                    "badge").strip()
            else:
                self.arresting_officer_badge = nan
        else:
            self.arresting_officer_name = nan
            self.arresting_officer_badge = nan

        self.arrest_date = handle_nulls(
            re.search("\d{2}\/\d{2}\/\d{4} \d{4}", select_line(self.block, 1)))

    def get_case_details(self):
        self.court_date = handle_nulls(
            re.search("\d{2}\/\d{2}\/\d{4}", select_line(self.block, 3)))

        prosecutor = re.search(
            "(?<=^)[(USAO)(OAG)(Traffic) &]+(?=     )", select_line(self.block, 3), flags=re.M)
        if prosecutor is not None:
            self.prosecutor = prosecutor.group().strip()
        else:
            self.prosecutor = handle_nulls(
                re.search("(?<=^)[(USAO)(OAG)(Traffic) &]+(?=     )", self.block))

        assigned_defense = re.search("(?<=Assigned To: ).+\)", self.block)

        if assigned_defense is not None:  # handles cases where there is no assigned defense
            self.assigned_name = handle_nulls(re.search(
                ".+(?= \()", assigned_defense.group()))
            self.assigned_affiliation = handle_nulls(re.search(
                "(?<=\().+(?=\))", assigned_defense.group()))
        else:
            self.assigned_name = nan
            self.assigned_affiliation = nan

        self.charges = handle_nulls(re.search(
            "(?<=Release\n)(?s:.)*(?=Assigned To)", self.block, flags=re.M), strip=True)

        self.pdid = handle_nulls(
            re.search("[0-9]{6}(?=     |$)", select_line(self.block, 1), flags=re.M))

        self.ccn = handle_nulls(
            re.search("[0-9]{8}(?=     |$)", select_line(self.block, 2), flags=re.M))

        self.codef = handle_nulls(
            re.search(r"(?<=CODEF )/d{2}|(?<=CODEF)/d{2}", self.block))

        # searches the whole block for multiple flags that can exist anywhere in the block
        dv = re.search("(?<=     )DV(?=     |$)", self.block, flags=re.M)

        if dv is not None:
            self.dv_flag = 1
        else:
            self.dv_flag = 0

        si = re.search("(?<=     )SI(?=     |$)", self.block, flags=re.M)

        if si is not None:
            self.si_flag = 1
        else:
            self.si_flag = 0

        p = re.search("(?<=     )P(?=     |$)", self.block, flags=re.M)

        if p is not None:
            self.p_flag = 1
        else:
            self.p_flag = 0

        np = re.search("(?<=     )NP(?=     |$)", self.block, flags=re.M)

        if np is not None:
            self.np_flag = 1
        else:
            self.np_flag = 0

#TODO create scrape_block function

def scrape_lulist(page, quiet=True, print_errors=False):
    '''
    Pulls all information from each lockup block on a lockup sheet page 

    Returns a DataFrame. 
    '''
    # reset iter
    lunum_list = [int(item.group("number")) for item in re.finditer(
        r"^\s+(?P<number>\d{2,3})(?= )", page, flags=re.M)]
    lunum = re.finditer(r"^\s+(?P<number>\d{2,3})(?= )", page, flags=re.M)

    lunum_raw = create_lunums(
        lu_text=page, lu_regex=r"^\s+(?P<number>\d{2,3})(?= )")
    lunum = validate_normalize_lunums(lunum_raw)

    d = []

    # loop through all lock up numbers
    for lu in lunum:
        scraper_warnings = nan

        num = lu.number

        if not lu.is_missing:
            try:
                block = lu.block

            # sometimes just the LU number cant be read this creates an observation for the next LU and notes the error
            # then captures the data for the current LU using the endpos of the next block

            except KeyError:  # TODO fix this to catch the way this error will not occur......
                print(f"WARNING: Key Error affecting {num+1}")

                try:
                    court_date_fallback = d[-1].get('court_date')
                except IndexError:
                    court_date_fallback = nan

                block = page[lu.start():startpos[lunum_list[lunum_list.index(num)+1]]]

                # If cant find LU number go find the second instance of the arrest date (the first attribute in every LU block)
                # Pull data for that LU
                errored_num = num + 1
                error_finder = list(re.finditer(
                    "\d{2}\/\d{2}\/\d{4} \d{4}", block))
                if len(error_finder) >= 2:
                    errored_start = error_finder[1].start()
                    errored_block = block[errored_start:len(block)]
                    error_fallback_flag = 1
                    print("fall back success :) partial info entered")

                    ErroredLUNum = LockUpBlock(
                        errored_num, errored_block, errored_lu=True)

                    d.append({
                        'court_date': court_date_fallback,
                        'lockup_number': errored_num,
                        'true_name': ErroredLUNum.true_name,
                        'name': ErroredLUNum.name,
                        'race': ErroredLUNum.race,
                        'gender': ErroredLUNum.gender,
                        'age': ErroredLUNum.age,
                        'scraper_warnings': f"KeyError, PDFReader could not find {num+1} fell back to arrest date start;"
                    })

                else:
                    errored_block = block
                    error_fallback_flag = 0
                    print("fall back failure :( LU # will be skipped")

                    d.append(
                        {
                            'court_date': court_date_fallback,
                            'lockup_number': errored_num,
                            'scraper_warnings': f"KeyError, PDFReader could not find {num+1};"
                        }
                    )

                if print_errors:
                    with open("output/temp/errored_blocks.txt", "a") as f:
                        f.write(f"""
                                ------------------------------------------
                                ---BLOCK TEXT FOR {num+1}---
                                ---Arrest date fall back: {error_fallback_flag}---
                                ------------------------------------------
                                """ + errored_block)

            # deal with leading newlines
            block = re.sub(r"\n+(?=\s{,25}(\d{2,3}) )", '', block)

            CurrentLUNum = LockUpBlock(num, block)

            if not quiet:
                print(f"""
                    Pulling LU# {CurrentLUNum.lu_number}...
                    age: {CurrentLUNum.age}
                    gender: {CurrentLUNum.gender}
                    race: {CurrentLUNum.race}
                    true name: {CurrentLUNum.true_name}
                    name: {CurrentLUNum.name}
                    attorney: {CurrentLUNum.assigned_name} from {CurrentLUNum.assigned_affiliation}
                    arresting_officer: {CurrentLUNum.arresting_officer_name} {CurrentLUNum.arresting_officer_badge}
                    arrest date time: {CurrentLUNum.arrest_date}
                    charges: {CurrentLUNum.charges}
                    prosecutor: {CurrentLUNum.prosecutor}
                    ------------------------------------------
                    """)

            d.append(
                {
                    'court_date': CurrentLUNum.court_date,
                    'lockup_number': num,
                    'arrest_number': CurrentLUNum.arrest_number,
                    'prosecutor': CurrentLUNum.prosecutor,
                    'true_name': CurrentLUNum.true_name,
                    'name': CurrentLUNum.name,
                    'race': CurrentLUNum.race,
                    'gender': CurrentLUNum.gender,
                    'age': CurrentLUNum.age,
                    'defense_name': CurrentLUNum.assigned_name,
                    'defense_affiliation': CurrentLUNum.assigned_affiliation,
                    'arresting_officer_name': CurrentLUNum.arresting_officer_name,
                    'arresting_officer_badge': CurrentLUNum.arresting_officer_badge,
                    'arrest_date': CurrentLUNum.arrest_date,
                    'charges': CurrentLUNum.charges,
                    'pdid': CurrentLUNum.pdid,
                    'ccn': CurrentLUNum.ccn,
                    'codef': CurrentLUNum.codef,
                    'dv_flag': CurrentLUNum.dv_flag,
                    'si_flag': CurrentLUNum.si_flag,
                    'p_flag': CurrentLUNum.p_flag,
                    'np_flag': CurrentLUNum.np_flag,
                    'scraper_warnings': scraper_warnings
                }
            )
        else:
            try:
                court_date_fallback = d[-1].get('court_date')
            except IndexError:
                court_date_fallback = nan

            d.append(
                {
                    'court_date': court_date_fallback,
                    'lockup_number': num,
                    'scraper_warnings': f"PDF Reader Error; Could not find LU block text for {num}"
                }
            )
       
    df = pd.DataFrame(d)
    
    if not quiet:
        print(df.head(10))
    return df


if __name__ == '__main__':
    # Test with file
    test_file = '/Users/viviennemonteiro/Projects/DC Courtwatch/lockupscraper/LockUpScraper2.0/output/legacy_test_output.txt'

    with open(test_file, 'r') as file:
        test_text = file.read()

    # Create LuNum objects
    lu_objects = create_lunums(lu_text=test_text)

    # Display results
    print("\n" + "="*60)
    print(f"Created {len(lu_objects)} LuNum objects")
    print("="*60)

    # Show first few
    for lu in lu_objects[:3]:
        print(f"\nLU Number: {lu.number}")
        print(f"  Position: {lu.start} to {lu.end}")
        print(f"  Block span: {lu.block_start} to {lu.block_end}")
        print(f"  Block preview: {lu.block[:100]}...")  # First 100 chars

    # Test Validation
    lu_objects_clean = validate_normalize_lunums(lu_objects)
