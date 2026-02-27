
#if __cplusplus <= 201402L
#  include <experimental/string_view>
namespace std {
  using string_view = std::experimental::string_view;
}
#endif
#include "hipo4/reader.h"
#include "hipo4/writer.h"
#include "hipo4/event.h"
#include "hipo4/dictionary.h"
