# https://www.home-assistant.io/integrations/python_script/
# Call your new python_script.hello_world service (with parameters) from the Services.
# name: Test
name = data.get("name", "world")
logger.info("Hello %s", name)
hass.bus.fire(name, {"wow": "from a Python script!"})
