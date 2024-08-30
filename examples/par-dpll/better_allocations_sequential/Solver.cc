#include <vector>
#include <math.h>
#include <iostream>
#include <thread>
#include <algorithm>
#include <tuple>
#include <map>
#include <functional>
using namespace std;

 enum ClauseState {
        UNSAT,
        SAT,
        UNDEF
    };





class Solver {

    
    public:
    std::vector<std::vector<int>> clauses;
    int num_clauses;
    int nvars;
    int num_propagations; 
    vector<int> var_activities;
    map<int, vector<vector<int>>> variable_to_clauses;



    bool compare_vars(int var, int var2) {
        return var_activities[var-1] >= var_activities[var2-1];
    }

    void backtrack(std::vector<int> &sol, int &currentVar,std::vector<int> &decisionsLeft, std::vector<tuple<int,int>> &trail) {
        tuple<int,int> finalDecision = trail.back();
        int finalDecisionVar = get<0>(finalDecision);
        int finalDecisionType = get<1>(finalDecision);

        while(sol.at(finalDecisionVar-1) == UNSAT || finalDecisionType == 1) {
            

            sol[finalDecisionVar-1] = UNDEF;
            trail.pop_back();
            decisionsLeft.push_back(finalDecisionVar);
            if (trail.empty())
                return;
            else
            {
                finalDecision = trail.back();
                finalDecisionVar = get<0>(finalDecision);
                finalDecisionType = get<1>(finalDecision);
            }
        }
        finalDecisionVar = get<0>(finalDecision);
        finalDecisionType = get<1>(finalDecision);


        if(sol.at(finalDecisionVar-1) == SAT) {
            sol[finalDecisionVar-1] = UNSAT;
            return;
        }

    }
    typedef std::tuple<std::vector<int>,
            std::vector<tuple<int,int>>,
            std::vector<int>,
            bool> result_tuple;
    void remove_lit(std::vector<int> &lits, int lit)
    {
       lits.erase(std::remove(lits.begin(), lits.end(), lit), lits.end()); 
    }

    result_tuple do_propagations(std::vector<int> &prop_lits,
                                std::vector<int> solution,
                                std::vector<tuple<int,int>> trail,
                                std::vector<int> &decisionsLeft,
                                vector<int> &potential_propagations
                                 )
    {   
        while(!prop_lits.empty()) {
            int l = prop_lits.back();
            prop_lits.pop_back();
            remove_lit(decisionsLeft,abs(l));
            trail.push_back({abs(l),1});
            if (l > 0 && (solution.at(l - 1) != UNSAT || solution.at(l - 1) == UNDEF))
                solution.at(l - 1) = SAT;
            else if (l < 0 && (solution.at(abs(l) - 1) != SAT || solution.at(abs(l) - 1) == UNDEF))
                solution.at(abs(l) - 1) = UNSAT;
            else return {{},{},{},false};
            potential_propagations.push_back(l);
        }
        return {solution,trail,decisionsLeft,true};
    }

    bool propagate(std::vector<int> &prop_lits,
                                std::vector<int> &solution,
                                std::vector<tuple<int,int>>&trail,
                                std::vector<int> &decisionsLeft,
                                std::vector<int> &potential_propagations )
        {   

            num_propagations++;
            result_tuple res_tuple = do_propagations(prop_lits,solution,trail,decisionsLeft,potential_propagations);
            if (std::get<3>(res_tuple)) {
                solution = std::get<0>(res_tuple);
                trail = std::get<1>(res_tuple);
                decisionsLeft = std::get<2>(res_tuple);
                return true;
            } else return false;
        }



    bool search(std::vector<int> &solution)
    {

        std::vector<int> decisionsLeft;
        decisionsLeft.reserve(nvars);
        for(int i=nvars;i>0;i--) {
            decisionsLeft.push_back(i);
        }
        std::vector<int> possible_propagators = find_unit_clauses();
        std::vector<tuple<int,int>> trail;
        trail.reserve(nvars);
        int currentVar = 0;
        int i = 1;
        std::vector<int> prop_lits;
        prop_lits.reserve(nvars);
        find_prop_lits(solution,prop_lits,possible_propagators);
        if(!propagate(prop_lits,solution,trail,decisionsLeft, possible_propagators))
            return false;
            else if (decisionsLeft.empty()) return check(solution);

        do {
            prop_lits.clear();
            find_prop_lits(solution,prop_lits,possible_propagators);
            possible_propagators.clear();
            ClauseState isSat = check(solution);
            if (!prop_lits.empty()) {
                if(propagate(prop_lits,solution,trail,decisionsLeft,possible_propagators))  {
                    prop_lits.clear();
                    isSat = check(solution);
                    if(isSat == UNDEF) {
                        continue;
                        possible_propagators.clear();
                    }  else if (isSat == SAT) return true;
                } else{
                 prop_lits.clear();
                 }
                };


            if (isSat == SAT) {
                return true;
            }


            else if (isSat == UNSAT)
            {
                backtrack(solution, currentVar, decisionsLeft, trail);
                possible_propagators.push_back(get<0>(trail.back()));
                if (trail.empty())
                    return false;
            }
            else
            {
                sort(decisionsLeft.begin(),decisionsLeft.end(),[this](int a, int b){
                    if (var_activities[a-1]==var_activities[b-1])
                      return a < b;                    
                    else return var_activities[a-1] < var_activities[b-1];
                    });
                int decision = decisionsLeft.back();
                decisionsLeft.pop_back();
                trail.push_back({decision,0});
                possible_propagators.push_back(decision);
                solution.at(decision-1) = SAT;
            }



        } while(true);


    }

    





       ClauseState literal_status(int &l,std::vector<int> &solution){
        if(solution.at(abs(l)-1) == UNDEF) {
                return UNDEF;
            } else if (solution.at(abs(l)-1) == SAT && l > 0 || solution.at(abs(l)-1) == UNSAT && l < 0) {
                return SAT;
            } else return UNSAT;
    }

    int is_unit(std::vector<int> &clause,std::vector<int> &solution) {
        int num_sat = 0;
        int num_undef = 0;
        int undef_lit = 2;
        for(int &l : clause) {
            ClauseState lit_status = literal_status(l,solution);
            if (lit_status == SAT) {
                num_sat++;
            } else if (lit_status == UNDEF) {
                undef_lit = l;
                num_undef++;
            } 
        }
        if (num_sat >= 1) {
            return false;
        } else if (num_undef == 1)
        {
            return undef_lit;
        } else return false;
        
    }

    

    std::vector<int> find_prop_lits(std::vector<int> &solution,vector<int> &prop_lits ,vector<int> &possible_propagators)
    {
        for (int  &possible_prop : possible_propagators) {
           vector<vector<int>>* possible_clauses = &variable_to_clauses[abs(possible_prop)];
        for(std::vector<int> &clause : *possible_clauses){
            int lit = is_unit(clause,solution);
            if (lit != 0) {
                bool included = false;
                for(int &l : prop_lits) {
                    if (abs(l) == abs(lit)) {
                        included = true;
                    }
                
                
                }
                if (!included) prop_lits.push_back(lit);
            }
            

        } 
    }

        return prop_lits;
    }
   ClauseState check(std::vector<int> &solution) {
    bool sat = true;
    for(std::vector<int> &clause : clauses) {
        ClauseState cstate = check_partial_clause(clause,solution);
        if(cstate == UNDEF) {
        return UNDEF;
        } else if(cstate == UNSAT) {
        return UNSAT;
        
        } else {
        }
        }
    return SAT;
    }


    ClauseState check_partial_clause(std::vector<int> &clause,std::vector<int> &solution) {
        bool sat = false;
        bool undef = true;
        for(int &l : clause) {

        int lit_state = solution.at(abs(l)-1);
        if(lit_state == UNDEF) return (ClauseState) lit_state;
        else if((lit_state == SAT && l > 0) || (lit_state == UNSAT && l < 0)) return SAT;
        } 
        return UNSAT;

    }

    void print_Trail(vector<tuple<int, int>> trail)
    {
    for (tuple<int,int> x : trail){
        cout << "{" << get<0>(x) << " " << get<1>(x) << "}, " ;

    }
    cout << endl;
    }

   void print_vector(std::vector<int> v) {
        for(int x : v) {
            std::cout << x << " ";
        }
        std::cout << std::endl;
   }


   void calc_variable_to_clauses()
   {
    var_activities.resize(nvars,0);
    for(vector<int> clause : clauses) {
        for(int l : clause) {
            variable_to_clauses[abs(l)].push_back(clause);
            var_activities[abs(l)-1]++;
        }
    }

   }


    vector<int> find_unit_clauses() {
        vector<int> unit_clauses;
        for(vector<int> c : clauses) {
            if(c.size()==1) {
                unit_clauses.push_back(c[0]);
            }
        }
        return unit_clauses;
    }



std::vector<int> initSol(int nvars) {
    std::vector<int> initSolution;
    initSolution.resize(nvars,(int)UNDEF); 
    return initSolution;
}


   bool solve() {
    calc_variable_to_clauses();
    std::vector<int> sol = initSol(nvars);
    bool sat = search(sol);
    return sat;
   }


};
