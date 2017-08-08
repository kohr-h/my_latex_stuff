#!/usr/bin/env python3

from collections import OrderedDict
import argparse
import sys

REMOVE_FIELDS = 'abstract,file,note,url,urldate'
REMOVE_FIELDS_HELP = (
    'Comma-separated list of fields to remove. '
    'Default: {}'.format(REMOVE_FIELDS)
    )


# Avoid closing default file descriptors

class StdIn(object):
    def __enter__(self):
        return sys.stdin

    def __exit__(*args, **kwargs):
        pass


class StdOut(object):
    def __enter__(self):
        return sys.stdout

    def __exit__(*args, **kwargs):
        pass


stdin = StdIn()
stdout = StdOut()


parser = argparse.ArgumentParser(
    description='Strip unnecessary stuff from BibTeX files'
    )

parser.add_argument(
    '-i', '--infile', default=stdin, type=argparse.FileType('r'),
    help='Input BibTeX file. Default: standard input')
parser.add_argument(
    '-o', '--outfile', default=stdout, type=argparse.FileType('w'),
    help='Output file. Default: standard output')
parser.add_argument(
    '-f', '--remove-fields', default=REMOVE_FIELDS, type=str,
    help=REMOVE_FIELDS_HELP)

args = parser.parse_args()
infile = args.infile
outfile = args.outfile
remove_fields = args.remove_fields.split(',')
remove_fields = tuple(s.strip() for s in remove_fields)


def next_entry_lines(file):
    in_entry = False
    num_open_braces = 0
    lines = []

    for line in file:
        if line.startswith('@') and not in_entry:
            # New entry
            in_entry = True
            lines.append(line)
            num_open_braces += line.count('{') - line.count('}')
        elif not in_entry:
            # Before any entry, skip line
            continue
        else:
            lines.append(line)
            num_open_braces += line.count('{') - line.count('}')
            if num_open_braces == 0:
                # Done with entry, stop
                break

    return tuple(lines)


def group_entries(entry_lines):
    entry_dict = OrderedDict()
    num_open_braces = 1
    skip_key = False
    cur_key = ''
    entry_type, entry_label = entry_lines[0].split('{', maxsplit=1)
    entry_type = entry_type.strip()[1:]
    entry_label = entry_label.lstrip().rstrip(',\n')
    entry_dict['entry_type'] = entry_type
    entry_dict['label'] = entry_label

    for line in entry_lines[1:]:
        if not line.strip():
            continue

        if num_open_braces == 1:
            num_open_braces += line.count('{') - line.count('}')
            if num_open_braces == 0:
                break
            # New field, get key and (first part of) value
            key, val = line.split('=', maxsplit=1)
            key = key.strip()
            val = val.lstrip().rstrip(',\n')
            if key in remove_fields or len(key.split()) > 1:
                skip_key = True
            else:
                skip_key = False
                cur_key = key
                entry_dict[cur_key] = val

        else:
            num_open_braces += line.count('{') - line.count('}')
            if not skip_key:
                entry_dict[cur_key] += ' ' + line.strip()

    return entry_dict


def dump_entry(entry_dict, file):
    lines = []
    firstline = ('@' + entry_dict['entry_type'] +
                 '{' + entry_dict['label'] + ',\n')
    lines.append(firstline)

    for key, val in entry_dict.items():
        if key in ('entry_type', 'label'):
            continue
        line = key + ' = ' + val + ',\n'
        lines.append(line)

    lines[-1] = lines[-1].rstrip(',\n') + '\n'
    lines.append('}\n\n')
    file.writelines(lines)


count = 0
with infile as f_in, outfile as f_out:
    while True:
        entry_lines = next_entry_lines(f_in)
        if not entry_lines:
            break
        entry_dict = group_entries(entry_lines)
        dump_entry(entry_dict, f_out)
        count += 1


infile_name = 'stdin' if infile == stdin else infile.name
outfile_name = 'stdout' if outfile == stdout else outfile.name
print('{} entries read from {} and written to {}'.format(count, infile_name,
                                                         outfile_name),
      file=sys.stderr)
