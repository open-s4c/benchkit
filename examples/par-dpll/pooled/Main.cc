#include <iostream>
#include <fstream>
#include <vector>
#include <thread>
#include <string>
#include <string.h>
#include <sstream>
#include "Solver.cc"
struct Parser {
    std::string current;
    int line = 0;
    int nvars = 0;
    int nclauses = 0;
    std::vector<std::vector<int>> clauses;
};

void skipWhitespace(Parser &parser) {
    while (parser.current[parser.line] == ' ' || parser.current[parser.line] == '\t' || parser.current[parser.line] == '\r') {
        parser.line++;
    }
}

void parseHeader(Parser &parser) {
    skipWhitespace(parser);
    if (parser.current[parser.line] != 'p') {
        throw std::runtime_error("Expected header at line " + std::to_string(parser.line));
    }
    parser.line++;
    skipWhitespace(parser);
    if (parser.current.substr(parser.line, 3) != "cnf") {
        throw std::runtime_error("Expected 'cnf' in header at line " + std::to_string(parser.line));
    }
    parser.line += 3;
    skipWhitespace(parser);
    std::istringstream iss(parser.current.substr(parser.line));
    iss >> parser.nvars >> parser.nclauses;
}

std::vector<int> parseClause(Parser &parser) {
    std::vector<int> clause;
    std::istringstream iss(parser.current.substr(parser.line));
    int literal;
    while (iss >> literal) {
        if (literal != 0) 
        clause.push_back(literal);
    }
    return clause;
}

  Parser parseDimacs(const std::string &filename) {
    std::ifstream file(filename);
    if (!file.is_open()) {
        throw std::runtime_error("Could not open file");
    }

    Parser parser;
    std::string line;
    while (std::getline(file, line)) {
        if (line.empty() || line[0] == 'c') {
            continue;
        }
        if(line[0] == '%') break;
        parser.current = line;
        if (line[0] == 'p') {
            parseHeader(parser);
        } else {
            parser.line = 0;
            std::vector<int> clause = parseClause(parser);
            parser.clauses.push_back(clause);
            if (!clause.empty()) {
                parser.nclauses--;
            }
        }
    }

    file.close();
    return parser;
}


int main(int argc, char *argv[]) {
    std::vector<std::vector<int>> clauses;
    int nvars;
    if (argc < 4) {
        std::cerr << "Usage: ./dimacs_parser <dimacs_file>" << std::endl;
        return 1;
    }

    try {
        Parser p =  parseDimacs(argv[1]);
        clauses = p.clauses;
        nvars =  p.nvars;
    } catch (const std::exception &e) {
        std::cerr << e.what() << std::endl;
        return 1;
    }

    int num_threads = 1;
    cout << argv[2] << endl;
    if(strncmp(argv[2],"-t",2) == 0) {
        num_threads = atoi(argv[3]);
        cout << num_threads << endl;
        if(num_threads < 1 || num_threads > INT32_MAX){ 
            throw invalid_argument("Invalid number of threads");
        }
    } else {
            throw invalid_argument("Please specify a number of threads");
    }


    Solver s(num_threads);
    s.clauses = clauses;
    s.nvars = nvars;


    bool satisfiability = s.solve();

    std::cout << "STATISTICS:\n";
    std::cout << "Activities: ";
    s.print_vector(s.var_activities);


    std::cout << "Sat? " << satisfiability << std::endl;
    return 0;
}
