from app.modules.business.listing.prompt import (
    OpenAIPromptTemplate,
    PromptSectionTemplate,
)


def test_section_to_str_includes_name_and_contents():
    section = PromptSectionTemplate(name="#Role", contents=["line1", "line2"])
    out = section.to_str()
    assert "#Role" in out
    assert "line1" in out
    assert "line2" in out


def test_section_nested_and_variable_substitution():
    parent = PromptSectionTemplate(name="#Parent", contents=["price is $price"])
    child = PromptSectionTemplate(name="#Child", contents=["child line"])
    parent.add_section(child)
    parent.add_variables({"price": "2 tỷ"})
    out = parent.to_str()
    assert "price is 2 tỷ" in out
    assert "#Child" in out
    assert "child line" in out


def test_prompt_template_to_api_message_user_only():
    tmpl = OpenAIPromptTemplate(model_name="x")
    tmpl.add_section(PromptSectionTemplate(name="#Role", contents=["be nice"]))
    messages = tmpl.to_api_message()
    assert messages == [{"role": "user", "content": tmpl.to_str()}]
    assert "be nice" in messages[0]["content"]


def test_prompt_template_to_api_message_system_and_user():
    tmpl = OpenAIPromptTemplate()
    tmpl.add_section(PromptSectionTemplate(name="#Role", contents=["sys"]))
    tmpl.add_user_message("hello")
    messages = tmpl.to_api_message()
    assert [m["role"] for m in messages] == ["system", "user"]
    assert messages[1]["content"] == "hello"
