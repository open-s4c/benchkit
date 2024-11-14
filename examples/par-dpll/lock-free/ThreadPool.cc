#include <pthread.h>
#include <functional>
#include <thread>
#include <vector>
#include <queue>
#include <mutex>
#include <condition_variable>
#include <iostream>
using namespace std;


void print_vector(std::vector<int> v) {
        for(int x : v) {
            std::cout << x << " ";
        }
        std::cout << std::endl;
   }
class ThreadPool
{
private:
    int num_thrs;
    queue<function<void()>> jobQueue;
    vector<thread> threads;
    mutex queue_lock;
    condition_variable mutex_condition;
    bool should_stop = false;
    
public:

    ThreadPool() {}

    ThreadPool(int num_threads){
        num_thrs = num_threads;
    }
    ~ThreadPool() {}

    void ThreadLoop() {
        while(true) {
            function<void()> job = [](){
            };
            
            {
                std::unique_lock<mutex> lock(queue_lock);
                mutex_condition.wait(lock, [this] {
                    return !jobQueue.empty() || should_stop;
                });
                if(should_stop) return;
                job = jobQueue.front();
                jobQueue.pop();
            }
            job();

        }

    }

    int queue_size() {
        return jobQueue.size();
    }

    void start(int num_thrs) {
        this->num_thrs = num_thrs;
        threads.reserve(num_thrs);
        for(int i = 0; i < num_thrs; i++) {
            threads.emplace_back(&ThreadPool::ThreadLoop,this);
        }
    };


    void stop() {
        {
            unique_lock<mutex> lock(queue_lock);
            should_stop = true;
        }
        mutex_condition.notify_all();
        for (thread &thr : threads)
        {   
            
            thr.join();
        }
        threads.clear();
    };


    void enqueueJob(const std::function<void()>& job) {
      {  std::unique_lock<mutex> lock(queue_lock);
        jobQueue.push(job);
      }
      mutex_condition.notify_one();
    };

    bool busy() {
    bool poolbusy;
    {   
        std::unique_lock<std::mutex> lock(queue_lock);
        poolbusy = !jobQueue.empty();
    }
    return poolbusy;
}

    

};


