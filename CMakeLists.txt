cmake_minimum_required(VERSION 3.16)

project(qbridge
  VERSION 1.0.0
  DESCRIPTION "State-vector quantum circuit simulator with matching C++, Python and JavaScript engines"
  LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

if(NOT CMAKE_BUILD_TYPE AND NOT CMAKE_CONFIGURATION_TYPES)
  set(CMAKE_BUILD_TYPE Release CACHE STRING "Build type" FORCE)
endif()

option(QBRIDGE_BUILD_TESTS "Build the qbridge unit tests" ON)
option(QBRIDGE_ENABLE_WARNINGS "Enable strict compiler warnings" ON)

# Header-only core; consumers only need the include directory.
add_library(qbridge INTERFACE)
target_include_directories(qbridge INTERFACE "${CMAKE_CURRENT_SOURCE_DIR}/include")

if(QBRIDGE_ENABLE_WARNINGS)
  if(MSVC)
    target_compile_options(qbridge INTERFACE /W4)
  else()
    target_compile_options(qbridge INTERFACE -Wall -Wextra -Wpedantic)
  endif()
endif()

add_executable(qbridge_cli src/main.cpp)
target_link_libraries(qbridge_cli PRIVATE qbridge)

if(QBRIDGE_BUILD_TESTS)
  enable_testing()
  add_executable(qbridge_tests tests/test_statevector.cpp)
  target_link_libraries(qbridge_tests PRIVATE qbridge)
  add_test(NAME statevector COMMAND qbridge_tests)
  set_tests_properties(statevector PROPERTIES
    WORKING_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}")
endif()

install(TARGETS qbridge_cli RUNTIME DESTINATION bin)
install(DIRECTORY include/ DESTINATION include)
install(DIRECTORY circuits/ DESTINATION share/qbridge/circuits)
