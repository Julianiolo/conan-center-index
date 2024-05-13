#include <cstdlib>
#include <iostream>
#include "niftilib/nifti1_io.h"


int main(void) {
    std::cout << nifti_short_order() << std::endl;

    return EXIT_SUCCESS;
}
