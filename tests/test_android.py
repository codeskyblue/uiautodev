from uiautodev.driver.android import parse_xml
from uiautodev.model import WindowSize

xml = """
<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>
<hierarchy rotation="0">
  <node display-id="0" index="0" text="" resource-id="" class="android.widget.FrameLayout" hint="" bounds="[20,30][1020,2030]">
    <node display-id="1" index="1" text="" resource-id="com.android.systemui:id/backdrop" hint="">
      <node index="0" text="" resource-id="com.android.systemui:id/backdrop_back" hint="" />
    </node>
    <node display-id="0" NAF="true" index="2" text="" resource-id="com.android.systemui:id/scrim_behind" class="android.view.View" package="com.android.systemui" content-desc="" checkable="false" checked="false" clickable="true" enabled="true" focusable="true" focused="false" scrollable="false" long-clickable="false" password="false" selected="false" visible-to-user="true" bounds="[0,0][1080,2340]" drawing-order="2" hint="" />
  </node>
</hierarchy>
"""

def test_parse_xml():
    node = parse_xml(xml.strip(), WindowSize(1000, 1000))
    assert node.name == "hierarchy"
    assert len(node.children) == 1
    assert node.rect is None

    childnode = node.children[0]
    assert childnode.name == "android.widget.FrameLayout"
    assert len(childnode.children) == 2
    assert childnode.rect is not None
    assert childnode.rect.x == 20
    assert childnode.rect.y == 30
    assert childnode.rect.width == 1000
    assert childnode.rect.height == 2000


def test_parse_xml_display_id():
    node = parse_xml(xml.strip(), WindowSize(1000, 1000), display_id=0)
    assert node.name == "hierarchy"
    assert len(node.children) == 1

    childnode = node.children[0]
    assert childnode.name == "android.widget.FrameLayout"
    assert len(childnode.children) == 1