import arcpy
arcpy.CheckOutExtension('Spatial')
arcpy.env.overwriteOutput = True

BELOW_GRIDCODE = 1
ABOVE_GRIDCODE = 2
ELEVATION_LAYER = 'elevation'
POPULATION_LAYER = 'population'

def create_remap_range(break_value, raster_file):
    """Creates a remap range used to reclassify a raster"""
    raster = arcpy.Raster(raster_file)
    below = [raster.minimum, break_value, BELOW_GRIDCODE]
    above = [break_value, raster.maximum, ABOVE_GRIDCODE]
    return arcpy.sa.RemapRange([below, above])


def new_elevation_raster(break_value, raster_file, reclass_field="VALUE"):
    """creates a reclassified elevation raster"""
    remap_table = create_remap_range(break_value, raster_file)
    return arcpy.sa.Reclassify(raster_file, reclass_field, remap_table)


def create_elevation_polygon(break_value, raster_file, output_polygon,
                             reclass_field="VALUE"):
    """creates a polygon file with areas classified as below or
    above a given elevation

    Keyword arguments:
    break_value    -- the elevation to determine above and below
    raster_file    -- the digital elevation model
    output_polygon -- the file to store the elevation polygon
    reclass_field  -- the field in the elevation raster with the elevation value (
                      default 'VALUE')
    """ 
    new_raster = new_elevation_raster(break_value, raster_file, reclass_field)
    arcpy.RasterToPolygon_conversion(new_raster, output_polygon)
    return output_polygon


def sum_field(feature, field):
    """sums all of a given numberical field of a given feature"""
    cursor = arcpy.da.SearchCursor(feature, [field])
    val = 0
    for row in cursor:
        val = val + row[0]
    return val


def sum_below_elevation(population_feature, elevation_raster, elevation,
                        spatial_relationships, population_field):
    """Return the number of people below a certain elevation.

    Keyword arguments:
    population_feature    -- a shapefile containing population information
    elevation_raster      -- a digitial elevation for the region
    elevation             -- the elevation to use in the calculation
    spatial_relationships -- the list of spatial relationships used to calculate
                             overlap by ArcGIS
    population_field      -- the field in the population file with population data
    """
    # create the elevation polygon
    # (polygons classify area as below or above elevation)
    elevation_polygon = "in_memory/%s" % ELEVATION_LAYER
    elevation_polygon = create_elevation_polygon(elevation, elevation_raster,
                                                 elevation_polygon)
    # create layers for elevation and population
    arcpy.MakeFeatureLayer_management(elevation_polygon, ELEVATION_LAYER)
    arcpy.MakeFeatureLayer_management(population_feature, POPULATION_LAYER)
    # select polygons below a certain elevation
    elevation_query = '"GRIDCODE" = %s' % BELOW_GRIDCODE
    arcpy.SelectLayerByAttribute_management(ELEVATION_LAYER, 'NEW_SELECTION', 
                                            elevation_query)
    results = []
    for relationship in spatial_relationships:
        arcpy.SelectLayerByLocation_management(POPULATION_LAYER, 
                                               overlap_type=relationship, 
                                               select_features=ELEVATION_LAYER,
                                               selection_type='NEW_SELECTION')
        sum = sum_field(POPULATION_LAYER, population_field)
        results.append((relationship, sum))
    return results

def create_population_function(population_feature, elevalation_raster,
                               spatial_relationships, population_field):
    funct = lambda e: sum_below_elevation(population_feature, elevation_raster,
                                          e, spatial_relationships, population_field)
    return funct
