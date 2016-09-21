from flask import Flask


app = Flask(__name__)

with open("uphpd") as f:
    config = {k: v for (k, v) in
              zip(["user", "password", "host", "port", "database"],
                  filter(bool, f.read().splitlines()))}


@app.route('/')
def root():
    return "The openMod.sh landing page."

if __name__ == '__main__':
    app.run(debug=True)

