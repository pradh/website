# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: subject_page.proto
"""Generated protocol buffer code."""
from google.protobuf.internal import builder as _builder
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import symbol_database as _symbol_database
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x12subject_page.proto\x12\x0b\x64\x61tacommons\"l\n\x0eSeverityFilter\x12\x0c\n\x04prop\x18\x01 \x01(\t\x12\x14\n\x0c\x64isplay_name\x18\x05 \x01(\t\x12\x0c\n\x04unit\x18\x02 \x01(\t\x12\x13\n\x0blower_limit\x18\x03 \x01(\x01\x12\x13\n\x0bupper_limit\x18\x04 \x01(\x01\"\x9b\x04\n\rEventTypeSpec\x12\n\n\x02id\x18\x01 \x01(\t\x12\x0c\n\x04name\x18\x02 \x01(\t\x12\x18\n\x10\x65vent_type_dcids\x18\x03 \x03(\t\x12\r\n\x05\x63olor\x18\x04 \x01(\t\x12<\n\x17\x64\x65\x66\x61ult_severity_filter\x18\x05 \x01(\x0b\x32\x1b.datacommons.SeverityFilter\x12[\n\x1aplace_type_severity_filter\x18\n \x03(\x0b\x32\x37.datacommons.EventTypeSpec.PlaceTypeSeverityFilterEntry\x12<\n\x0c\x64isplay_prop\x18\x06 \x03(\x0b\x32&.datacommons.EventTypeSpec.DisplayProp\x12\x15\n\rend_date_prop\x18\x07 \x03(\t\x12\x1d\n\x15polygon_geo_json_prop\x18\x08 \x01(\t\x12\x1a\n\x12path_geo_json_prop\x18\t \x01(\t\x1a[\n\x1cPlaceTypeSeverityFilterEntry\x12\x0b\n\x03key\x18\x01 \x01(\t\x12*\n\x05value\x18\x02 \x01(\x0b\x32\x1b.datacommons.SeverityFilter:\x02\x38\x01\x1a?\n\x0b\x44isplayProp\x12\x0c\n\x04prop\x18\x01 \x01(\t\x12\x14\n\x0c\x64isplay_name\x18\x02 \x01(\t\x12\x0c\n\x04unit\x18\x03 \x01(\t\"\xe3\x03\n\x0cPageMetadata\x12\x10\n\x08topic_id\x18\x01 \x01(\t\x12\x12\n\ntopic_name\x18\x02 \x01(\t\x12\x12\n\nplace_dcid\x18\x03 \x03(\t\x12Q\n\x15\x63ontained_place_types\x18\x04 \x03(\x0b\x32\x32.datacommons.PageMetadata.ContainedPlaceTypesEntry\x12\x45\n\x0f\x65vent_type_spec\x18\x05 \x03(\x0b\x32,.datacommons.PageMetadata.EventTypeSpecEntry\x12\x39\n\x0bplace_group\x18\x06 \x03(\x0b\x32$.datacommons.PageMetadata.PlaceGroup\x1a:\n\x18\x43ontainedPlaceTypesEntry\x12\x0b\n\x03key\x18\x01 \x01(\t\x12\r\n\x05value\x18\x02 \x01(\t:\x02\x38\x01\x1aP\n\x12\x45ventTypeSpecEntry\x12\x0b\n\x03key\x18\x01 \x01(\t\x12)\n\x05value\x18\x02 \x01(\x0b\x32\x1a.datacommons.EventTypeSpec:\x02\x38\x01\x1a\x36\n\nPlaceGroup\x12\x14\n\x0cparent_place\x18\x01 \x01(\t\x12\x12\n\nplace_type\x18\x02 \x01(\t\"h\n\x0bStatVarSpec\x12\x10\n\x08stat_var\x18\x01 \x01(\t\x12\r\n\x05\x64\x65nom\x18\x02 \x01(\t\x12\x0c\n\x04unit\x18\x03 \x01(\t\x12\x0f\n\x07scaling\x18\x04 \x01(\x01\x12\x0b\n\x03log\x18\x05 \x01(\x08\x12\x0c\n\x04name\x18\x06 \x01(\t\"\xb3\x01\n\x0fRankingTileSpec\x12\x14\n\x0cshow_highest\x18\x01 \x01(\x08\x12\x13\n\x0bshow_lowest\x18\x02 \x01(\x08\x12\x16\n\x0e\x64iff_base_date\x18\x05 \x01(\t\x12\x15\n\rhighest_title\x18\x06 \x01(\t\x12\x14\n\x0clowest_title\x18\x07 \x01(\t\x12\x15\n\rranking_count\x18\n \x01(\x05\x12\x19\n\x11show_multi_column\x18\x0b \x01(\x08\"u\n\x18\x44isasterEventMapTileSpec\x12\x1c\n\x14point_event_type_key\x18\x01 \x03(\t\x12\x1e\n\x16polygon_event_type_key\x18\x02 \x03(\t\x12\x1b\n\x13path_event_type_key\x18\x03 \x03(\t\"9\n\x11HistogramTileSpec\x12\x16\n\x0e\x65vent_type_key\x18\x01 \x01(\t\x12\x0c\n\x04prop\x18\x02 \x01(\t\"\x9d\x01\n\x10TopEventTileSpec\x12\x16\n\x0e\x65vent_type_key\x18\x01 \x01(\t\x12\x14\n\x0c\x64isplay_prop\x18\x02 \x03(\t\x12\x17\n\x0fshow_start_date\x18\x03 \x01(\x08\x12\x15\n\rshow_end_date\x18\x04 \x01(\x08\x12\x14\n\x0creverse_sort\x18\x05 \x01(\x08\x12\x15\n\rranking_count\x18\x06 \x01(\x05\"\x89\x01\n\x0fScatterTileSpec\x12\x1b\n\x13highlight_top_right\x18\x01 \x01(\x08\x12\x1a\n\x12highlight_top_left\x18\x02 \x01(\x08\x12\x1e\n\x16highlight_bottom_right\x18\x03 \x01(\x08\x12\x1d\n\x15highlight_bottom_left\x18\x04 \x01(\x08\"(\n\x0b\x42\x61rTileSpec\x12\x19\n\x11x_label_link_root\x18\x01 \x01(\t\"c\n\rGaugeTileSpec\x12/\n\x05range\x18\x01 \x01(\x0b\x32 .datacommons.GaugeTileSpec.Range\x1a!\n\x05Range\x12\x0b\n\x03min\x18\x01 \x01(\x01\x12\x0b\n\x03max\x18\x02 \x01(\x01\"\xb6\x06\n\x04Tile\x12\r\n\x05title\x18\x01 \x01(\t\x12\x13\n\x0b\x64\x65scription\x18\x02 \x01(\t\x12(\n\x04type\x18\x03 \x01(\x0e\x32\x1a.datacommons.Tile.TileType\x12\x14\n\x0cstat_var_key\x18\x04 \x03(\t\x12\x19\n\x11\x63omparison_places\x18\x07 \x03(\t\x12\x1b\n\x13place_dcid_override\x18\x0b \x01(\t\x12\x39\n\x11ranking_tile_spec\x18\x05 \x01(\x0b\x32\x1c.datacommons.RankingTileSpecH\x00\x12M\n\x1c\x64isaster_event_map_tile_spec\x18\x06 \x01(\x0b\x32%.datacommons.DisasterEventMapTileSpecH\x00\x12<\n\x13top_event_tile_spec\x18\x08 \x01(\x0b\x32\x1d.datacommons.TopEventTileSpecH\x00\x12\x39\n\x11scatter_tile_spec\x18\t \x01(\x0b\x32\x1c.datacommons.ScatterTileSpecH\x00\x12=\n\x13histogram_tile_spec\x18\n \x01(\x0b\x32\x1e.datacommons.HistogramTileSpecH\x00\x12\x31\n\rbar_tile_spec\x18\x0c \x01(\x0b\x32\x18.datacommons.BarTileSpecH\x00\x12\x35\n\x0fgauge_tile_spec\x18\r \x01(\x0b\x32\x1a.datacommons.GaugeTileSpecH\x00\"\xd3\x01\n\x08TileType\x12\r\n\tTYPE_NONE\x10\x00\x12\x08\n\x04LINE\x10\x01\x12\x07\n\x03\x42\x41R\x10\x02\x12\x07\n\x03MAP\x10\x03\x12\x0b\n\x07SCATTER\x10\x04\x12\r\n\tBIVARIATE\x10\x05\x12\x0b\n\x07RANKING\x10\x06\x12\r\n\tHIGHLIGHT\x10\x07\x12\x0f\n\x0b\x44\x45SCRIPTION\x10\x08\x12\t\n\x05GAUGE\x10\r\x12\r\n\tHISTOGRAM\x10\n\x12\x12\n\x0ePLACE_OVERVIEW\x10\x0b\x12\r\n\tTOP_EVENT\x10\x0c\x12\x16\n\x12\x44ISASTER_EVENT_MAP\x10\tB\x10\n\x0etile_type_spec\"\xf1\x01\n\x05\x42lock\x12\r\n\x05title\x18\x01 \x01(\t\x12\x13\n\x0b\x64\x65scription\x18\x02 \x01(\t\x12\x10\n\x08\x66ootnote\x18\x05 \x01(\t\x12*\n\x07\x63olumns\x18\x03 \x03(\x0b\x32\x19.datacommons.Block.Column\x12*\n\x04type\x18\x04 \x01(\x0e\x32\x1c.datacommons.Block.BlockType\x1a*\n\x06\x43olumn\x12 \n\x05tiles\x18\x01 \x03(\x0b\x32\x11.datacommons.Tile\".\n\tBlockType\x12\r\n\tTYPE_NONE\x10\x00\x12\x12\n\x0e\x44ISASTER_EVENT\x10\x01\"\xdf\x01\n\x08\x43\x61tegory\x12\r\n\x05title\x18\x01 \x01(\t\x12\x13\n\x0b\x64\x65scription\x18\x02 \x01(\t\x12=\n\rstat_var_spec\x18\x04 \x03(\x0b\x32&.datacommons.Category.StatVarSpecEntry\x12\"\n\x06\x62locks\x18\x03 \x03(\x0b\x32\x12.datacommons.Block\x1aL\n\x10StatVarSpecEntry\x12\x0b\n\x03key\x18\x01 \x01(\t\x12\'\n\x05value\x18\x02 \x01(\x0b\x32\x18.datacommons.StatVarSpec:\x02\x38\x01\"k\n\x11SubjectPageConfig\x12+\n\x08metadata\x18\x01 \x01(\x0b\x32\x19.datacommons.PageMetadata\x12)\n\ncategories\x18\x02 \x03(\x0b\x32\x15.datacommons.Categoryb\x06proto3')

_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, globals())
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'subject_page_pb2', globals())
if _descriptor._USE_C_DESCRIPTORS == False:

  DESCRIPTOR._options = None
  _EVENTTYPESPEC_PLACETYPESEVERITYFILTERENTRY._options = None
  _EVENTTYPESPEC_PLACETYPESEVERITYFILTERENTRY._serialized_options = b'8\001'
  _PAGEMETADATA_CONTAINEDPLACETYPESENTRY._options = None
  _PAGEMETADATA_CONTAINEDPLACETYPESENTRY._serialized_options = b'8\001'
  _PAGEMETADATA_EVENTTYPESPECENTRY._options = None
  _PAGEMETADATA_EVENTTYPESPECENTRY._serialized_options = b'8\001'
  _CATEGORY_STATVARSPECENTRY._options = None
  _CATEGORY_STATVARSPECENTRY._serialized_options = b'8\001'
  _SEVERITYFILTER._serialized_start=35
  _SEVERITYFILTER._serialized_end=143
  _EVENTTYPESPEC._serialized_start=146
  _EVENTTYPESPEC._serialized_end=685
  _EVENTTYPESPEC_PLACETYPESEVERITYFILTERENTRY._serialized_start=529
  _EVENTTYPESPEC_PLACETYPESEVERITYFILTERENTRY._serialized_end=620
  _EVENTTYPESPEC_DISPLAYPROP._serialized_start=622
  _EVENTTYPESPEC_DISPLAYPROP._serialized_end=685
  _PAGEMETADATA._serialized_start=688
  _PAGEMETADATA._serialized_end=1171
  _PAGEMETADATA_CONTAINEDPLACETYPESENTRY._serialized_start=975
  _PAGEMETADATA_CONTAINEDPLACETYPESENTRY._serialized_end=1033
  _PAGEMETADATA_EVENTTYPESPECENTRY._serialized_start=1035
  _PAGEMETADATA_EVENTTYPESPECENTRY._serialized_end=1115
  _PAGEMETADATA_PLACEGROUP._serialized_start=1117
  _PAGEMETADATA_PLACEGROUP._serialized_end=1171
  _STATVARSPEC._serialized_start=1173
  _STATVARSPEC._serialized_end=1277
  _RANKINGTILESPEC._serialized_start=1280
  _RANKINGTILESPEC._serialized_end=1459
  _DISASTEREVENTMAPTILESPEC._serialized_start=1461
  _DISASTEREVENTMAPTILESPEC._serialized_end=1578
  _HISTOGRAMTILESPEC._serialized_start=1580
  _HISTOGRAMTILESPEC._serialized_end=1637
  _TOPEVENTTILESPEC._serialized_start=1640
  _TOPEVENTTILESPEC._serialized_end=1797
  _SCATTERTILESPEC._serialized_start=1800
  _SCATTERTILESPEC._serialized_end=1937
  _BARTILESPEC._serialized_start=1939
  _BARTILESPEC._serialized_end=1979
  _GAUGETILESPEC._serialized_start=1981
  _GAUGETILESPEC._serialized_end=2080
  _GAUGETILESPEC_RANGE._serialized_start=2047
  _GAUGETILESPEC_RANGE._serialized_end=2080
  _TILE._serialized_start=2083
  _TILE._serialized_end=2905
  _TILE_TILETYPE._serialized_start=2676
  _TILE_TILETYPE._serialized_end=2887
  _BLOCK._serialized_start=2908
  _BLOCK._serialized_end=3149
  _BLOCK_COLUMN._serialized_start=3059
  _BLOCK_COLUMN._serialized_end=3101
  _BLOCK_BLOCKTYPE._serialized_start=3103
  _BLOCK_BLOCKTYPE._serialized_end=3149
  _CATEGORY._serialized_start=3152
  _CATEGORY._serialized_end=3375
  _CATEGORY_STATVARSPECENTRY._serialized_start=3299
  _CATEGORY_STATVARSPECENTRY._serialized_end=3375
  _SUBJECTPAGECONFIG._serialized_start=3377
  _SUBJECTPAGECONFIG._serialized_end=3484
# @@protoc_insertion_point(module_scope)
