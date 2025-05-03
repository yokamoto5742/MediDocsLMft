from utils.constants import DEFAULT_SECTION_NAMES


def format_discharge_summary(summary_text):
    processed_text = (
        summary_text.replace('*', '')
        .replace('＊', '')
        .replace('#', '')
        .replace(' ', '')
    )

    return processed_text


def parse_discharge_summary(summary_text):
    sections = {section: "" for section in DEFAULT_SECTION_NAMES}

    section_aliases = {
        "禁忌・アレルギー": "禁忌/アレルギー"
    }

    lines = summary_text.split('\n')
    current_section = None

    for line in lines:
        line = line.strip()
        if not line:
            continue

        found_section = False
        for section in list(sections.keys()) + list(section_aliases.keys()):
            if section in line:
                if section in section_aliases:
                    current_section = section_aliases[section]
                else:
                    current_section = section

                line = line.replace(section, "").replace(":", "").strip()
                found_section = True
                break

        if current_section and line and not found_section:
            if sections[current_section]:
                sections[current_section] += "\n" + line
            else:
                sections[current_section] = line
        elif current_section and line and found_section:
            sections[current_section] = line

    return sections
