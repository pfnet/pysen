## Render pysen.gif

```bash
$ terminalizer render src/pysen.yml -o imgs/pysen.gif
$ terminalizer render src/pysen_vim.yml -o imgs/pysen_vim.gif
```

## Build docker image for pysen-test

```bash
$ docker build -t quay.io/pysen/pysen-test .
$ docker push quay.io/pysen/pysen-test
```
