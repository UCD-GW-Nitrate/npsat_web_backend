from django.contrib import admin

# Register your models here.

from . import models

admin.site.register(models.Region)
admin.site.register(models.Crop)
admin.site.register(models.CropGroup)
admin.site.register(models.MantisServer)
admin.site.register(models.Scenario)
admin.site.register(models.ResultPercentile)


class ModelRunModificationInline(admin.TabularInline):
    model = models.Modification


class ModelRunAdmin(admin.ModelAdmin):
    inlines = [ModelRunModificationInline]


admin.site.register(models.ModelRun, ModelRunAdmin)
admin.site.register(models.Modification)
