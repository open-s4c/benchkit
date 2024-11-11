from benchkit.utils.ftrace import FTrace


def main() -> None:
    path = "./tests/tmp/ftrace_dump"
    trace = FTrace(path)
    spans = trace.query_spans()
    counts = trace.query_counts()
    for span in spans:
        print(span)
    for count in counts:
        print(count)


if __name__ == "__main__":
    main()
