import { Hono } from "hono";
import { serve } from "@hono/node-server";
import Provider from "./provider.js";

const app = new Hono();

const provider = new Provider(process.env.NWC_CONNECTION_STRING);

app.get("/", (c) => c.text("Hello Hono!"));

app.get("/api/hello", (c) => {
  return c.json({
    message: "Hello from the API!",
  });
});

app.post('/api/run-command', async (c) => {
  const payload = await c.req.json();
  const {action,data} = payload;
  const result = await provider[action](data);
  return c.json({result});
})

const port = 3000;
console.log(`Server is running on port ${port}`);

serve({
  fetch: app.fetch,
  port,
});
