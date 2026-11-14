namespace Shop.Application.UnitTests.Jobs;

public sealed class OrderJobsTests
{
    [Fact]
    public void Expand_QueuesOneMessagePerRoute()
    {
        var job = new ExpansionJob(Routes.Of(("fulfilment", "orders-out"), ("returns", "returns-out")));

        Assert.Equal(2, job.Expand());
    }

    [Fact]
    public void Deliver_SkipsARouteWithNoClient()
    {
        var job = new DeliveryJob(Routes.Of(("fulfilment", "orders-out")));

        Assert.Equal(["fulfilment"], job.Clients());
    }
}
