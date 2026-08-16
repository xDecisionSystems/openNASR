from openNASR.cli import build_parser


def test_cli_exposes_check_command_and_force_option():
    args = build_parser().parse_args(["check", "--force"])

    assert args.command == "check"
    assert args.force
