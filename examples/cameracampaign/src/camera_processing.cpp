#include <librealsense2/rs.hpp>
#include <opencv2/opencv.hpp>
#include <iostream>
#include <Eigen/Core>
#include <chrono>
using namespace std;

int main(int argc, char** argv) {
    
    if (argc != 2) {
        cerr << "Usage: " << argv[0] << " <duration_in_seconds>" << endl;
        return 1;
    }
    int duration_seconds = stoi(argv[1]);

    using namespace std::chrono;
    
    rs2::pipeline pipe;
    rs2::config cfg;
    cfg.enable_stream(RS2_STREAM_DEPTH, 640, 480, RS2_FORMAT_Z16, 90);
    pipe.start(cfg);
    
    auto start_time = high_resolution_clock::now();
    auto end_time = start_time + seconds(duration_seconds);

    int frame_count = 0;

    while (high_resolution_clock::now() < end_time) {
        auto start = std::chrono::high_resolution_clock::now();
        rs2::frameset frames = pipe.wait_for_frames();
        rs2::depth_frame depth_frame = frames.get_depth_frame();
        if (!depth_frame) {
            cerr << "Error retrieving frames!" << endl;
            continue;
        }

        rs2::stream_profile depth_stream = depth_frame.get_profile();
        rs2_intrinsics intrinsics = depth_stream.as<rs2::video_stream_profile>().get_intrinsics();

        cv::Mat current_image_depth(cv::Size(depth_frame.get_width(), depth_frame.get_height()), CV_16U, (void*)depth_frame.get_data(), cv::Mat::AUTO_STEP);

        frame_count++;

    }
    
    cout << "Final counter value: " << frame_count << endl;
    return 0;
}

