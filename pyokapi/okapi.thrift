
namespace py okapi
namespace java okapi

struct Response{
    1: i32 code,
    2: map<string, string> headers,
    3: binary body
}

service InvokeService{         

    Response InvokeAPI(1:string api_path, 2:string method, 3:map<string, string> arg, 4:map<string, string> headers, 5:binary body)

}
