import asyncio
import json
from typing import Set

from aiohttp import web
from aiohttp.web import Application, Request, Response, StreamResponse

from aiohttp_sse import sse_response

channels = web.AppKey("channels", Set[asyncio.Queue[str]])


async def chat(_request: Request) -> web.Response:
    d = """
    <html>
      <head>
        <title>Tiny Chat</title>
        <script
        src="//ajax.googleapis.com/ajax/libs/jquery/1.9.1/jquery.min.js">
        </script>
        <style>
        .messages {
          overflow: scroll;
          height: 200px;
        }
        .messages .sender{
          float: left;
          clear: left;
          width: 120px;
          margin-right: 10px;
          text-align: right;
          background-color: #ddd;
        }
        .messages .message{
          float: left;
        }
        form {
          display: inline;
        }

        </style>
        <script>
          $(function(){
            var source = new EventSource("/subscribe");
            source.addEventListener('message', function(event) {
              console.log(event.data)
              message = JSON.parse(event.data);
              $('.messages').append(
              "<div class=sender>"+message.sender+"</div>"+
              "<div class=message>"+message.message+"</div>");
            });

            $('form').submit(function(e){
              e.preventDefault();
              $.post('/everyone',
                {
                  sender: $('.name').text(),
                  message: $('form .message').val()
                })
              $('form .message').val('')
            });

            $('.change-name').click(function(){
              name = prompt("Enter your name:");
              $('.name').text(name);
            });
         });
        </script>
      </head>
      <body>
        <div class=messages></div>
        <button class=change-name>Change Name</button>
        <span class=name>Anonymous</span>
        <span>:</span>
      <form>
        <input class="message" placeholder="Message..."/>
        <input type="submit" value="Send" />
      </form>
      </body>
    </html>

    """
    return Response(text=d, content_type="text/html")


async def message(request: Request) -> web.Response:
    app = request.app
    data = await request.post()

    for queue in app[channels]:
        payload = json.dumps(dict(data))
        await queue.put(payload)
    return Response()


async def subscribe(request: Request) -> EventSourceResponse:
    async with sse_response(request) as response:
        app = request.app
        queue: asyncio.Queue[str] = asyncio.Queue()
        print("Someone joined.")
        app[channels].add(queue)
        try:
            while response.is_connected():
                payload = await queue.get()
                await response.send(payload)
                queue.task_done()
        finally:
            app[channels].remove(queue)
            print("Someone left.")
    return response


if __name__ == "__main__":
    app = Application()
    app[channels] = set()  # type: ignore[misc]

    app.router.add_route("GET", "/", chat)
    app.router.add_route("POST", "/everyone", message)
    app.router.add_route("GET", "/subscribe", subscribe)
    web.run_app(app, host="127.0.0.1", port=8080)
