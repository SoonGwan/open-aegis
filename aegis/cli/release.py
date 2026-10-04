"""Offline signed bundle creation/verification and pre-update backup."""
import argparse
import json
from ..releases import create_release,verify_release,prepare_update
from ..maintenance import WorkspaceBusy
from zipfile import BadZipFile


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    commands=parser.add_subparsers(dest='command',required=True)
    create=commands.add_parser('create')
    for name in ('wheel','web','lock','output','private-key','revision'):
        create.add_argument('--'+name,required=True)
    verify=commands.add_parser('verify')
    prepare=commands.add_parser('prepare')
    for command in (verify,prepare):
        command.add_argument('--bundle',required=True)
        command.add_argument('--public-key',required=True)
    prepare.add_argument('--database',required=True)
    prepare.add_argument('--output',required=True)
    args=vars(parser.parse_args());command=args.pop('command')
    try:
        result={'create':create_release,'verify':verify_release,'prepare':prepare_update}[command](**args)
    except (ValueError,OSError,WorkspaceBusy,BadZipFile) as exc:
        parser.error(str(exc))
    print(json.dumps(result,ensure_ascii=False))


if __name__=='__main__':main()
