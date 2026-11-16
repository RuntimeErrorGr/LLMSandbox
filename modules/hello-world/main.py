import platform

import sandbox_sdk as sdk

params = sdk.params()
sdk.log(f"Hello, {params['name']}! Running inside the sandbox.")
sdk.log(f"Python {platform.python_version()}, smoke test: {sdk.is_smoke_test()}")

sdk.write_result(
    summary=f"hello-world greeted {params['name']}",
    metrics={"python": platform.python_version(), "params": params},
)
