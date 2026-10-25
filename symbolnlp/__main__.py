import argparse
import json
import sys
from .core import Document, parse, render
from .rewording import paraphrase
from .alternations import RewriteContext, inventory


def main():
    parser = argparse.ArgumentParser(description="Non-LLM paraphrasing with variability and fidelity reports")
    commands = parser.add_subparsers(dest="command", required=True)
    rewrite = commands.add_parser("paraphrase", help="Rewrite text and report variability and fidelity")
    rewrite.add_argument("text", nargs="?", help="Text (default: stdin)")
    rewrite.add_argument("--candidates", type=int, default=16)
    rewrite.add_argument("--seed", type=int, help="Reproducible testing only; disables private randomness")
    rewrite.add_argument("--text-only", action="store_true", help="Emit only text for the receiving agent")
    commands.add_parser("alternations", help="List all 45 rules, risks, and context guards")
    rewrite.add_argument("--assume", action="append", default=[], help="Trusted context assumption (repeatable)")
    p = commands.add_parser("parse")
    p.add_argument("text", nargs="?", help="Text (default: stdin)")
    p.add_argument("--preserve-vocabulary", action="store_true")
    r = commands.add_parser("render")
    r.add_argument("--vocabulary", choices=["canonical", "preserve", "random"], default="canonical")
    r.add_argument("--structure", choices=["active", "passive", "random"], default="active")
    r.add_argument("--seed", type=int)
    args = parser.parse_args()
    try:
        if args.command == "alternations":
            print(json.dumps(inventory(), indent=2))
        elif args.command == "paraphrase":
            result = paraphrase(args.text if args.text is not None else sys.stdin.read(),
                                candidates=args.candidates, seed=args.seed,
                                context=RewriteContext(frozenset(args.assume)))
            if args.text_only:
                if result.text is None:
                    parser.exit(2, "symbolnlp: Unsupported passage; use JSON output for coverage details\n")
                print(result.text)
            else:
                print(json.dumps(result.to_dict(), indent=2))
                if result.text is None:
                    parser.exit(2)
        elif args.command == "parse":
            doc = parse(args.text if args.text is not None else sys.stdin.read(),
                        normalize=not args.preserve_vocabulary)
            print(json.dumps(doc.to_dict(), indent=2))
        else:
            doc = Document.from_dict(json.load(sys.stdin))
            print(render(doc, vocabulary=args.vocabulary, structure=args.structure, seed=args.seed))
    except (ValueError, KeyError, TypeError) as exc:
        parser.exit(2, f"symbolnlp: {exc}\n")


if __name__ == "__main__":
    main()
