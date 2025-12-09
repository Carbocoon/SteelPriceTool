#----------------------------------------------------------------
# Generated CMake target import file for configuration "Release".
#----------------------------------------------------------------

# Commands may need to know the format version.
set(CMAKE_IMPORT_FILE_VERSION 1)

# Import target "thrift::thrift" for configuration "Release"
set_property(TARGET thrift::thrift APPEND PROPERTY IMPORTED_CONFIGURATIONS RELEASE)
set_target_properties(thrift::thrift PROPERTIES
  IMPORTED_IMPLIB_RELEASE "D:/temp_documents/公司/SteelPriceTool/.conda-env/Library/lib/thriftmd.lib"
  IMPORTED_LOCATION_RELEASE "D:/temp_documents/公司/SteelPriceTool/.conda-env/Library/bin/thriftmd.dll"
  )

list(APPEND _cmake_import_check_targets thrift::thrift )
list(APPEND _cmake_import_check_files_for_thrift::thrift "D:/temp_documents/公司/SteelPriceTool/.conda-env/Library/lib/thriftmd.lib" "D:/temp_documents/公司/SteelPriceTool/.conda-env/Library/bin/thriftmd.dll" )

# Commands beyond this point should not need to know the version.
set(CMAKE_IMPORT_FILE_VERSION)
