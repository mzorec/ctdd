namespace Shop.Api.IntegrationTests;

public sealed class OpenApiDocumentTests(ApiFixture fixture)
{
    [Fact]
    public async Task OpenApiDocument_PublishesNoEmptySummaryOrDescription()
    {
        var document = await fixture.ReadOpenApiAsync();

        Assert.All(document.Operations, o => Assert.False(string.IsNullOrWhiteSpace(o.Summary)));
        Assert.All(document.Operations, o => Assert.False(string.IsNullOrWhiteSpace(o.Description)));
    }
}
