#!/usr/bin/env python3

# Read the user model
with open("backend/app/models/user.py", "r") as f:
    lines = f.readlines()

# Find the problematic section and fix it
fixed_lines = []
i = 0
phone_section_added = False
profile_section_added = False

while i < len(lines):
    line = lines[i]

    # Add the line to our fixed lines
    fixed_lines.append(line)

    # Check if we found the phone section
    if 'if hasattr(self, "phone") and self.phone:' in line:
        # Make sure the next line sets the phone correctly
        if i + 1 < len(lines) and 'result["phone"]' not in lines[i + 1]:
            fixed_lines.append('                result["phone"] = self.phone\n')
            phone_section_added = True

    # Check if we need to add the profile picture section
    if (
        phone_section_added
        and not profile_section_added
        and "except:" in line
        and i + 1 < len(lines)
        and "pass" in lines[i + 1]
    ):
        # We're at the end of the phone section, add the profile picture section
        fixed_lines.append(lines[i + 1])  # Add the 'pass' line

        # Now add our profile picture section
        fixed_lines.append("\n        try:\n")
        fixed_lines.append('            if hasattr(self, "profile_picture_url") and self.profile_picture_url:\n')
        fixed_lines.append('                result["profile_picture_url"] = self.profile_picture_url\n')
        fixed_lines.append("        except:\n")
        fixed_lines.append("            pass\n")

        profile_section_added = True
        i += 1  # Skip the 'pass' line since we already added it

    i += 1

# Write the fixed file
with open("backend/app/models/user.py", "w") as f:
    f.writelines(fixed_lines)

print("User model fixed successfully!")
