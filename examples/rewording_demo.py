"""Run with python3 -m examples.rewording_demo from the repository root."""
import json
from symbolnlp import paraphrase
from symbolnlp.rewording.evaluation import evaluate


def main():
    text = 'Alice helps Bob. On the building, a bird sat. Give me the butter.'
    result = paraphrase(text, seed=7)  # Testing only; omit seed in deployment.
    print(json.dumps(result.to_dict(), indent=2))
    evaluation = evaluate(['Alice helps Bob.', 'It is 90 degrees outside.'], trials=64)
    print(json.dumps(evaluation, indent=2))


if __name__ == '__main__':
    main()
